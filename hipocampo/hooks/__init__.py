"""Claude Code hooks, wired by plugin/hooks/hooks.json.

- session_start: git-derived bounded briefing injected at SessionStart.
- capture_sweep: Stop-hook sweep of capture candidates into the vault inbox.

Both read everything project-specific from brain.config.toml and never block.
"""
