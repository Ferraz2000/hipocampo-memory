#!/usr/bin/env python3
"""Stop hook: sweep the session transcript for un-captured candidates (durable
decisions, lessons, external sources) and write a sweep into the vault inbox for
later triage. Never blocks.

Implements the sleep-time-consolidation pattern: the agent's session leaves a
journal the human later triages via /registra. Everything project-specific
(triggers, internal hosts, inbox path, sweep type) comes from brain.config.toml.

Stop-hook stdin JSON: {"transcript_path", "session_id", "stop_hook_active"}.

Behavior:
- Skip if stop_hook_active (avoid loops) or if /registra was invoked this session.
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


def _iter_md(directory):
    if not directory.is_dir():
        return
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if fname.endswith(".md"):
                yield os.path.join(root, fname)


def scan_existing(cfg, exclude_path=None):
    """Returns (captured_urls, inbox_blob) for dedup. Best-effort, stdlib only."""
    inbox = str(cfg.inbox_dir)
    ex = os.path.abspath(exclude_path) if exclude_path else None
    captured = set()
    inbox_parts = []
    for path in list(_iter_md(cfg.raw_sources_dir)) + list(_iter_md(cfg.knowledge_dir)):
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


def _extract(ev):
    """(text, role) from a transcript event across common shapes."""
    content = ev.get("content") or ev.get("message", {}).get("content")
    if isinstance(content, list):
        text = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
    elif isinstance(content, str):
        text = content
    else:
        text = ""
    role = (ev.get("type") or ev.get("role")
            or (ev.get("message") or {}).get("role") or "").lower()
    return text, role


def scan_transcript(transcript_path, cfg):
    """Returns (triggers_hit, urls, registra_invoked)."""
    user_re = _trigger_re(cfg.capture_triggers)
    agent_re = _trigger_re(cfg.capture_agent_triggers)
    triggers_hit = []
    urls = set()
    registra_invoked = False
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
                registra_invoked = True
            pat = user_re if role == "user" else (agent_re if role == "assistant" else None)
            if pat is not None:
                for m in pat.finditer(text):
                    snippet = text[max(0, m.start() - 60): m.end() + 80].replace("\n", " ")
                    triggers_hit.append((m.group(0), redact(snippet.strip())))
            for u in URL_RE.findall(text):
                if is_external(u, cfg.capture_internal_hosts):
                    urls.add(redact(u))
    return triggers_hit, urls, registra_invoked


def _render_sweep(date, short, session_id, sweep_type, triggers_hit, urls):
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
             "> `/registra`, but capture candidates were detected. Triage each:",
             ">",
             "> - **Durable concept** → move to `knowledge/<area>/<slug>.md`",
             "> - **External source** → move to `raw/sources/<date>-<slug>.md`",
             "> - **Persona/preference** → append to your agent rules file (e.g. `.claude/rules/USER.md`)",
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
              "- [ ] Manual triage (or via `/registra <slug>`).",
              "- [ ] Delete this sweep after triage.", ""]
    return "\n".join(lines)


def main(argv=None):
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("stop_hook_active"):
        return 0

    transcript_path = payload.get("transcript_path")
    session_id = payload.get("session_id", "unknown")
    if not transcript_path or not os.path.exists(transcript_path):
        return 0

    try:
        cfg = _config.load_config(start=os.environ.get("CLAUDE_PROJECT_DIR"))
    except _config.ConfigError:
        return 0  # bad config shouldn't break the session's Stop hook
    cfg.inbox_dir.mkdir(parents=True, exist_ok=True)

    try:  # housekeeping: expire stale sweeps
        removed = inbox_decay.decay(cfg=cfg, apply=True)
        if removed:
            print(f"capture-sweep: {len(removed)} stale sweep(s) removed.", file=sys.stderr)
    except Exception:
        pass

    date = datetime.now().strftime("%Y-%m-%d")
    short = session_id[:8]
    out_path = cfg.inbox_dir / f"{date}-sweep-{short}.md"
    if out_path.exists():
        return 0

    triggers_hit, urls, registra_invoked = scan_transcript(transcript_path, cfg)
    if registra_invoked:
        return 0

    try:
        captured_urls, inbox_blob = scan_existing(cfg, exclude_path=str(out_path))
    except Exception:
        captured_urls, inbox_blob = set(), ""
    urls, triggers_hit = filter_new(urls, triggers_hit, captured_urls, inbox_blob)

    if not triggers_hit and not urls:
        return 0

    out_path.write_text(
        _render_sweep(date, short, session_id, cfg.inbox_sweep_type, triggers_hit, urls),
        encoding="utf-8")
    rel = os.path.relpath(out_path, cfg.repo_root)
    print(f"capture-sweep: {len(triggers_hit)} trigger(s) + {len(urls)} URL(s). Triage in {rel}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
