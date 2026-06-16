"""Agent lifecycle hooks, wired per platform.

- session_start: git-derived bounded briefing injected at session start.
- capture_sweep: session-end sweep of capture candidates into the vault inbox.
- ensure_githooks: point core.hooksPath at .githooks (web/ephemeral containers).

The logic is agent-agnostic; only the wiring differs per platform:

- Claude Code  → plugin/hooks/hooks.json (SessionStart / Stop)
- Codex CLI    → .codex/hooks.json        (SessionStart / Stop)
- Gemini CLI   → .gemini/settings.json    (SessionStart / SessionEnd)

All three CLIs pass a session-start `source` and an end-of-session
`transcript_path`, and accept `hookSpecificOutput.additionalContext` to inject
context. Everything project-specific is read from brain.config.toml. Hooks never
block (always exit 0).
"""

import os


def project_dir():
    """Best-effort repo/project root from the host agent's env, else cwd.

    Claude Code sets CLAUDE_PROJECT_DIR; Codex/Gemini run the hook with the
    project as cwd. config.load_config() walks up from here to find the config.
    """
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
