# templates/hooks/ — per-agent hook wiring

The hipocampo automations are agent-agnostic Python (`hipocampo.hooks.*`); only
the wiring differs per CLI. `brain-scripts-init` installs the right file for the
agents you use. All three pass a session-start `source` and an end-of-session
`transcript_path`, and accept `hookSpecificOutput.additionalContext`.

| Agent | File | Events |
|-------|------|--------|
| Claude Code | `plugin/hooks/hooks.json` (carried by the plugin) | `SessionStart`, `Stop` |
| Codex CLI | `.codex/hooks.json` (or `~/.codex/hooks.json`) | `SessionStart`, `Stop` |
| Gemini CLI | merge into `.gemini/settings.json` | `SessionStart`, `SessionEnd` |

All commands assume the `hipocampo` package is importable from the repo root
(vendored by `brain-scripts-init`, hence `PYTHONPATH=.`). `session_start` is run
with `--format json` so its briefing is injected as `additionalContext`.

## Codex (`codex/hooks.json`)

Copy to `.codex/hooks.json` (project-local) or `~/.codex/hooks.json` (user-level,
more reliable while project-local hooks are flaky). Non-managed hooks need trust:
run `/hooks` once in Codex to approve. **Codex hooks are experimental** (~v0.114)
and the transcript format is not a stable interface — the sweep degrades
gracefully if it can't parse an event.

## Gemini (`gemini/settings.hooks.json`)

This is a fragment: merge its `hooks` object into your `.gemini/settings.json`
(project or user). Gemini fires `SessionEnd` (with a `reason`) rather than `Stop`;
the sweep skips `reason == "clear"`.
