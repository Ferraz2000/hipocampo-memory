# plugin/ — Claude Code plugin

Installable bundle: generator + workflow skills and the two automation hooks.

```
plugin/
  .claude-plugin/plugin.json   # manifest (name, version, …)
  hooks/hooks.json             # SessionStart briefing + Stop capture-sweep
  skills/                      # SKILL.md per skill (Agent Skills open format)
```

## Install

```sh
/plugin marketplace add Ferraz2000/hipocampo
/plugin install hipocampo@hipocampo
```

The skills also work cross-agent (Codex `.agents/skills`, Gemini `.gemini/skills`)
via `npx skills add Ferraz2000/hipocampo`.

## Hooks and the python package

`hooks.json` runs `python3 -m hipocampo.hooks.{session_start,capture_sweep}`. The
hooks (and the git-hook/CI templates) need the `hipocampo` package importable
from the target repo — the `brain-scripts-init` skill vendors it at the repo
root (or it can be `pip install`ed). Both hooks are config-driven and never block.

## Skills

- **Generators:** `brain-init` (scaffold the vault), `brain-router-init`
  (generate the `AGENTS.md` router for the repo's language), `brain-scripts-init`
  (vendor scripts + git hooks + CI), `brain-update` (update vendored files).
- **Workflow:** `registra` (capture, write-gated), `busca` (search), `discovery`
  (broad vault read), `spec` (mini design doc).
