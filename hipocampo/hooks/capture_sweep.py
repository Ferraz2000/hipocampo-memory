#!/usr/bin/env python3
"""Session-end hook: sweep the session transcript for un-captured candidates
(durable decisions, lessons, external sources) and write a sweep into the vault
inbox for later triage. Never blocks.

Implements the sleep-time-consolidation pattern: the agent's session leaves a
journal the human later triages via /capture. Everything project-specific
(triggers, internal hosts, inbox path, sweep type) comes from brain.config.toml.

Wired as Claude Code `Stop`, Codex `Stop`, or Gemini `SessionEnd` — all pass a
`transcript_path` on stdin. Stdin JSON (fields vary by agent, all optional):
{"transcript_path", "session_id"/"sessionId", "stop_hook_active", "reason"}.

Behavior:
- Skip on stop_hook_active (Claude re-entrancy) or reason=="clear" (Gemini), or
  if /capture was invoked this session.
- Skip if a sweep file already exists for this session.
- Detect configured triggers (user-side and agent-side) + external URLs.
- Dedup against what's already captured (raw/sources, knowledge, pending inbox).
- Decay stale sweeps as housekeeping (reuses inbox_decay). Best-effort throughout.
"""

import json
import os
import re
import sys
from datetime import datetime

from .. import config as _config
from .. import inbox_decay
from ..mdutil import iter_md
from . import project_dir

URL_RE = re.compile(r"https?://[\w\-\.]+(?:/[\w\-\./?=&%#~+]*)?", re.IGNORECASE)

# Best-effort secret scrubbing: the sweep is an automated, ungated write, so we
# never want a pasted credential landing verbatim in the (git-versioned) inbox.
_SECRET_RES = [
    # key/identifier (incl. UNDERSCORE_JOINED env vars) followed by is/=/: and a value
    re.compile(r"(?i)\b\w*(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|"
               r"client[_-]?secret|authorization|bearer|credential)\w*\s*(?:is|=|:)\s*\S+"),
    re.compile(r"AKIA[0-9A-Z]{12,16}"),                 # AWS key id (also if snippet-truncated)
    re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b[a-z0-9._%+-]+:[^\s/@]{6,}@"),   # user:pass@ in a URL
    # Unlabeled high-entropy tokens — common shapes pasted without a keyword, so
    # the labeled rule above misses them. High-precision prefixes (near-zero
    # false positives) plus the standard JWT triple.
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),        # GitHub PAT / OAuth / app tokens
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"),   # OpenAI secret keys
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),      # Slack tokens
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),  # JWT
]


def redact(text):
    """Replace obvious secret shapes with [REDACTED]. Best-effort, not a guarantee."""
    for rx in _SECRET_RES:
        text = rx.sub("[REDACTED]", text)
    return text


def _trigger_re(words):
    if not words:
        return None
    alt = "|".join(re.escape(w) for w in words)
    return re.compile(r"(?<!\w)(" + alt + r")(?!\w)", re.IGNORECASE)


def is_external(url, internal_hosts):
    u = url.lower()
    return not any(h.lower() in u for h in internal_hosts)


def norm_url(url):
    return url.lower().rstrip("/).,;]>\"'")


def scan_existing(cfg, exclude_path=None):
    """Returns (captured_urls, inbox_blob) for dedup. Best-effort, stdlib only."""
    inbox = str(cfg.inbox_dir)
    ex = os.path.abspath(exclude_path) if exclude_path else None
    captured = set()
    inbox_parts = []
    for path in list(iter_md(cfg.raw_sources_dir)) + list(iter_md(cfg.knowledge_dir)):
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        for u in URL_RE.findall(text):
            captured.add(norm_url(u))
        if path.startswith(inbox + os.sep) and (ex is None or os.path.abspath(path) != ex):
            inbox_parts.append(text.lower())
    return captured, " ".join(inbox_parts)


def filter_new(urls, triggers_hit, captured_urls, inbox_blob):
    """Drop already-captured URLs and snippets already awaiting triage. Pure."""
    new_urls = {u for u in urls if norm_url(u) not in captured_urls}
    new_triggers = []
    for trigger, snippet in triggers_hit:
        core = snippet.lower().strip()[:80]
        if core and core in inbox_blob:
            continue
        new_triggers.append((trigger, snippet))
    return new_urls, new_triggers


def _content_text(content):
    """Flatten a content value across agent transcript shapes (str, or a list of
    parts each carrying `text`/`content`). Gemini uses `parts: [{text}]`; Claude
    uses `content: [{type:text, text}]`; Codex varies (format is not stable)."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        # e.g. {type:text, text:"..."} or {type:tool_result, content:[...]}
        return _content_text(content.get("text") or content.get("content") or "")
    if isinstance(content, list):
        # Recurse: a part may itself carry a nested list (e.g. a Claude
        # tool_result whose `content` is a list of blocks). Appending that list
        # straight into the join() raised "expected str instance, list found".
        return " ".join(t for t in (_content_text(c) for c in content) if t)
    return ""


def _extract(ev):
    """(text, role) from a transcript event across Claude/Codex/Gemini shapes."""
    msg = ev.get("message") if isinstance(ev.get("message"), dict) else {}
    # `parts` is Gemini's container; `content` is Claude/Codex's.
    content = (ev.get("content") if ev.get("content") is not None
               else msg.get("content") if msg.get("content") is not None
               else ev.get("parts") if ev.get("parts") is not None
               else msg.get("parts"))
    text = _content_text(content)
    role = (ev.get("role") or msg.get("role") or ev.get("type") or "").lower()
    # Normalize agent-specific role labels onto user/assistant.
    if role in ("human",):
        role = "user"
    elif role in ("model", "agent", "ai"):
        role = "assistant"
    return text, role


def scan_transcript(transcript_path, cfg):
    """Returns (triggers_hit, urls, capture_invoked)."""
    user_re = _trigger_re(cfg.capture_triggers)
    agent_re = _trigger_re(cfg.capture_agent_triggers)
    triggers_hit = []
    urls = set()
    capture_invoked = False
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            text, role = _extract(ev)
            if not text:
                continue
            low = text.lower()
            if any(v.lower() in low for v in cfg.capture_verbs):
                capture_invoked = True
            pat = user_re if role == "user" else (agent_re if role == "assistant" else None)
            if pat is not None:
                for m in pat.finditer(text):
                    snippet = text[max(0, m.start() - 60): m.end() + 80].replace("\n", " ")
                    triggers_hit.append((m.group(0), redact(snippet.strip())))
            for u in URL_RE.findall(text):
                if is_external(u, cfg.capture_internal_hosts):
                    urls.add(redact(u))
    return triggers_hit, urls, capture_invoked


def _render_sweep(date, short, session_id, sweep_type, triggers_hit, urls,
                  persona_file=".claude/rules/USER.md"):
    lines = ["---",
             f"title: 'Capture sweep — session {short} ({date})'",
             f"type: {sweep_type}",
             f"session_id: {session_id}",
             f"created: {date}",
             "status: triage",
             "pinned: false",
             "tags: [capture, sweep, automatic]",
             "---", "",
             f"# Automatic sweep — {date} ({short})", "",
             "> Generated by the capture-sweep Stop hook. The session ended without",
             "> `/capture`, but capture candidates were detected. Triage each:",
             ">",
             "> - **Durable concept** → move to `knowledge/<area>/<slug>.md`",
             "> - **External source** → move to `raw/sources/<date>-<slug>.md`",
             f"> - **Persona/preference** → append to your agent rules file (`{persona_file}`)",
             "> - **Not worth it** → delete this file",
             ">",
             "> ⚠ **SECURITY:** secret-shaped strings were auto-redacted (best-effort, not a"
             " guarantee). Review for any leaked credential/PII before committing this sweep.",
             ">",
             "> Boundary heuristic: contract (gated) vs concept (knowledge/) — see capture.md.",
             ""]
    if triggers_hit:
        lines += ["## Triggers detected", ""]
        seen = set()
        for trigger, snippet in triggers_hit[:30]:
            key = snippet[:120]
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- **{trigger}**: …{snippet}…")
        lines.append("")
    if urls:
        lines += ["## External URLs cited", ""]
        lines += [f"- {u}" for u in sorted(urls)[:30]]
        lines.append("")
    lines += ["## Next steps", "",
              "- [ ] Manual triage (or via `/capture <slug>`).",
              "- [ ] Delete this sweep after triage.", ""]
    return "\n".join(lines)


def _pending_header(persona_file=".claude/rules/USER.md"):
    """Header for the disposable draft-mode staging file (`.brain-cache/`)."""
    return "\n".join([
        "# Pending capture — review, don't commit",
        "",
        "> Disposable staging written by the capture-sweep hook (`capture.auto.mode",
        "> = draft`). Lives in `.brain-cache/` (gitignored) — **nothing here is in",
        "> durable memory yet.**",
        ">",
        "> Triage with `/capture --review`. The bullets below are regex-detected",
        "> **signals, not the final wording** — read each session's `transcript` for",
        "> full context and draft proper notes (proactive extraction), then file",
        "> each (concept → `knowledge/`, source → `raw/sources/`, persona →",
        f"> `{persona_file}`) or drop it. This file is deleted once triaged.",
        ">",
        "> ⚠ Secret-shaped strings were auto-redacted (best-effort). Re-check before filing.",
        "",
    ])


def _render_pending_block(date, short, triggers_hit, urls, max_candidates=7, transcript=None):
    """One per-session block of capture candidates as review checkboxes. Records
    the transcript pointer so `/capture --review` can reason over the real session
    (fresh-session review; degrades to the snippets if the transcript is gone)."""
    lines = [f"## Session {short} — {date}", ""]
    if transcript:
        lines += [f"> transcript: {transcript}", ""]
    seen = set()
    n = 0
    for trigger, snippet in triggers_hit:
        key = snippet[:120]
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- [ ] **{trigger}**: …{snippet}…")
        n += 1
        if n >= max_candidates:
            break
    for u in sorted(urls)[:max_candidates]:
        lines.append(f"- [ ] source: {u}")
    lines.append("")
    return "\n".join(lines)


def _write_pending(staging, date, short, session_id, triggers_hit, urls, cfg,
                   transcript=None):
    """Append this session's candidates to the disposable staging file. Idempotent
    per session (re-runs don't duplicate); creates the header once. Never touches
    the vault — the whole point of draft mode."""
    block = _render_pending_block(date, short, triggers_hit, urls, cfg.capture_auto_max,
                                  transcript=transcript)
    if staging.exists():
        prior = staging.read_text(encoding="utf-8")
        if f"session {short}".lower() in prior.lower():
            return  # already staged for this session
        staging.write_text(prior.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
    else:
        staging.parent.mkdir(parents=True, exist_ok=True)
        staging.write_text(_pending_header(cfg.persona_file) + "\n" + block + "\n",
                           encoding="utf-8")


def main(argv=None):
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    # Claude Code re-entrancy guard; Gemini SessionEnd `reason` (skip context
    # clears, not genuine session ends). Both absent on agents that don't send them.
    if payload.get("stop_hook_active") or payload.get("reason") == "clear":
        return 0

    transcript_path = payload.get("transcript_path")
    # session_id field name varies; fall back so the sweep filename still forms.
    session_id = payload.get("session_id") or payload.get("sessionId") or "unknown"
    if not transcript_path or not os.path.exists(transcript_path):
        return 0

    try:
        cfg = _config.load_config(start=project_dir())
    except _config.ConfigError:
        return 0  # bad config shouldn't break the session-end hook

    mode = cfg.capture_auto_mode
    if mode == "off":
        return 0

    date = datetime.now().strftime("%Y-%m-%d")
    short = session_id[:8]
    staging = cfg.cache_dir / "pending-capture.md"
    out_path = cfg.inbox_dir / f"{date}-sweep-{short}.md"

    if mode == "inbox":
        # Legacy path: sweep into the vault inbox + housekeeping decay. Draft mode
        # never touches the vault, so neither the mkdir nor the decay run there.
        cfg.inbox_dir.mkdir(parents=True, exist_ok=True)
        try:  # housekeeping: expire stale sweeps
            removed = inbox_decay.decay(cfg=cfg, apply=True)
            if removed:
                print(f"capture-sweep: {len(removed)} stale sweep(s) removed.", file=sys.stderr)
        except Exception:
            pass
        if out_path.exists():
            return 0

    triggers_hit, urls, capture_invoked = scan_transcript(transcript_path, cfg)
    if capture_invoked:
        return 0

    try:
        captured_urls, inbox_blob = scan_existing(cfg, exclude_path=str(out_path))
    except Exception:
        captured_urls, inbox_blob = set(), ""
    if mode == "draft" and staging.exists():
        try:  # dedup against candidates already staged but not yet reviewed
            inbox_blob += " " + staging.read_text(encoding="utf-8").lower()
        except OSError:
            pass
    urls, triggers_hit = filter_new(urls, triggers_hit, captured_urls, inbox_blob)

    if not triggers_hit and not urls:
        return 0

    if mode == "draft":
        _write_pending(staging, date, short, session_id, triggers_hit, urls, cfg,
                       transcript=transcript_path)
        rel = os.path.relpath(staging, cfg.repo_root)
        print(f"capture-sweep(draft): {len(triggers_hit)} candidate(s) + {len(urls)} "
              f"URL(s) staged in {rel} — review via /capture --review", file=sys.stderr)
        return 0

    out_path.write_text(
        _render_sweep(date, short, session_id, cfg.inbox_sweep_type, triggers_hit, urls,
                      persona_file=cfg.persona_file),
        encoding="utf-8")
    rel = os.path.relpath(out_path, cfg.repo_root)
    print(f"capture-sweep: {len(triggers_hit)} trigger(s) + {len(urls)} URL(s). Triage in {rel}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
