#!/usr/bin/env python3
"""SessionStart hook: inject a bounded, git-derived briefing as context.

The source is the real repo state (current branch, work ahead of the base
branch, recent merges, pending inbox sweeps), so it never goes stale — the one
sanctioned automatic context load (see context-budget.md). Cross-platform
(pure Python), config-driven (base branch), and capped so it can't blow the
budget. Never blocks.

Output formats (all three agents accept additionalContext at session start):
  --format plain  (default) raw briefing on stdout — Claude Code adds it as
                  context; Codex injects stdout as a developer message too.
  --format json   {"hookSpecificOutput": {"hookEventName": "SessionStart",
                  "additionalContext": <briefing>}} — required by Gemini CLI,
                  also accepted by Claude Code and Codex.
"""

import argparse
import json
import subprocess
import sys

from .. import config as _config
from . import project_dir

_CAP = 8000  # keep well under Claude Code's ~10k inline threshold


def _git(cfg, *args):
    try:
        out = subprocess.run(["git", *args], cwd=str(cfg.repo_root),
                             capture_output=True, text=True)
    except (FileNotFoundError, OSError):
        return ""
    return out.stdout if out.returncode == 0 else ""


def _resolve_base(cfg, branch):
    """First base ref that actually exists; None when nothing resolves."""
    for cand in (cfg.base_branch, f"origin/{cfg.base_branch}",
                 "main", "origin/main", "master", "origin/master"):
        if cand == branch:
            continue  # comparing a branch to itself is always zero
        if _git(cfg, "rev-parse", "--verify", "--quiet", cand).strip():
            return cand
    return None


def build_briefing(cfg):
    branch = _git(cfg, "rev-parse", "--abbrev-ref", "HEAD").strip() or "(detached)"
    base = _resolve_base(cfg, branch)

    lines = ["# Work in progress (git-derived — never stale)", ""]
    lines.append(f"## Current session — `{branch}`")

    if base is None:
        lines.append("- No base branch resolved (single-branch repo).")
    else:
        ahead = _git(cfg, "rev-list", "--count", f"{base}..HEAD").strip()
        if ahead and ahead != "0":
            log = _git(cfg, "log", "--oneline", f"{base}..HEAD", "-5").strip()
            lines.append(f"- {ahead} commit(s) ahead of {base}:")
            lines += [f"  - {ln}" for ln in log.splitlines()]
        else:
            lines.append(f"- No commits ahead of {base}.")
    lines.append("")

    merges = _git(cfg, "log", "--merges", "--oneline", "-5").strip()
    if merges:
        lines.append("## Recently merged")
        lines += [f"- {ln}" for ln in merges.splitlines()]
        lines.append("")

    inbox = cfg.inbox_dir
    if inbox.is_dir():
        sweeps = sorted(p.name for p in inbox.glob("*.md"))
        if sweeps:
            lines.append(f"## Pending inbox sweeps ({len(sweeps)}) — triage via /capture")
            lines += [f"- {s}" for s in sweeps[:10]]
            lines.append("")

    # Draft-mode (Phase 12) candidates staged in the disposable cache — surface
    # the reminder so the human reviews before they're lost to a cache wipe.
    pending = cfg.cache_dir / "pending-capture.md"
    if pending.is_file():
        rel = pending.relative_to(cfg.repo_root).as_posix()
        lines.append("## Pending capture — review via /capture --review")
        lines.append(f"- candidates staged in `{rel}` (not yet in the vault)")
        lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    if len(text) <= _CAP:
        return text
    # Truncate on a line boundary so we never emit half a markdown line.
    return text[:_CAP].rsplit("\n", 1)[0] + "\n"


def _emit(text, fmt):
    """Render the briefing in the requested output envelope."""
    if fmt == "json":
        return json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": text}})
    return text


def main(argv=None):
    # Deliberately do NOT read stdin: a blocking json.load() can hang the hook
    # until the SessionStart timeout, which fails the boot in some containers.
    # The payload is unused; not reading it is safe (the writer just gets SIGPIPE).
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--format", choices=("plain", "json"), default="plain")
    args, _ = ap.parse_known_args(sys.argv[1:] if argv is None else argv)
    try:
        cfg = _config.load_config(start=project_dir())
        sys.stdout.write(_emit(build_briefing(cfg), args.format))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
