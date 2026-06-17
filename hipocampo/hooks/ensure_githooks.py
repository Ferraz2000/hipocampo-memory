#!/usr/bin/env python3
"""SessionStart hook: ensure ``core.hooksPath`` points at ``.githooks``.

Web/ephemeral containers lose local git config; without this, the doc-sync
pre-commit gate silently never runs. Idempotent, silent, never blocks: only
acts when a ``.githooks`` directory exists and the config isn't already set.
Agent-agnostic (Claude Code / Codex / Gemini all run it at session start).
"""

import os
import subprocess
import sys

from . import project_dir


def main(argv=None):
    root = project_dir()
    hooks_dir = os.path.join(root, ".githooks")
    if not os.path.isdir(hooks_dir):
        return 0
    try:
        cur = subprocess.run(["git", "config", "core.hooksPath"], cwd=root,
                             capture_output=True, text=True).stdout.strip()
        if cur != ".githooks":
            subprocess.run(["git", "config", "core.hooksPath", ".githooks"],
                           cwd=root, capture_output=True)
    except (FileNotFoundError, OSError):
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
