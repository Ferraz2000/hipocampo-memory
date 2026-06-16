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
/plugin marketplace add Ferraz2000/hipocampo-memory
/plugin install hipocampo@hipocampo
```

The skills also work cross-agent (Codex `.agents/skills`, Gemini `.gemini/skills`)
via `npx skills add Ferraz2000/hipocampo-memory`.

## Hooks and the python package

`hooks.json` runs `python3 -m hipocampo.hooks.{session_start,capture_sweep}`. The
hooks (and the git-hook/CI templates) need the `hipocampo` package importable
from the target repo — the `brain-scripts-init` skill vendors it at the repo
root (or it can be `pip install`ed). Both hooks are config-driven and never block.

## Skills

- **Generators:** `brain-init` (scaffold the vault), `brain-router-init`
  (generate the `AGENTS.md` router for the repo's language), `brain-scripts-init`
  (vendor scripts + git hooks + CI), `brain-update` (update vendored files).
- **Workflow:** `capture` (write-gated), `search`, `discovery`
  (broad vault read), `spec` (mini design doc), `challenge` (confront a decision
  with the vault's past reversals), `discover-standards` (mine code → candidate
  convention insights), `garden` (lint/consolidation), `archive-closed` (compact
  terminal insights).
- **Insight lifecycle:** `from-roadmap` (what next), `promote` (insight → spec/
  ADR/issue), `implement` (build an approved spec), `execute-insight` (one insight,
  two commits), `weekly` (triage cycle), `postmortem` (lessons from a branch),
  `audit` (fact-check a page vs its sources), `low-token` (lean mode).
