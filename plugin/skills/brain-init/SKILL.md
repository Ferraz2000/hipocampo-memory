---
name: brain-init
description: Scaffold a hipocampo memory vault into the current project — creates brain.config.toml and the docs/brain skeleton (knowledge/index, capture.md, context-budget.md, note templates). Use when setting up agent memory in a repo that doesn't have a vault yet, or when the user says "init the brain", "set up the vault", "brain-init".
---

# brain-init — scaffold the vault

Create a durable, git-versioned, human-gated memory vault in this repo. Idempotent:
never overwrite an existing `.md`.

**Prerequisites:** ability to run `git` and Python (`python3`, or `python` on
Windows). In a restricted sandbox that blocks writes/process execution, these
skills cannot scaffold — say so instead of half-running.

## Steps

1. **Detect existing setup.** If `brain.config.toml` already exists, read it and
   reuse its answers. Otherwise gather, via ONE `AskUserQuestion` (4 questions —
   this is the whole interview; don't ask more):
   - **New or existing project?** (drives everything downstream: existing →
     `brain-router-init` detects and confirms; new/greenfield → it asks the
     stack questions instead)
   - **Solo or team?** (team → suggest a protected branch + PR review for the
     vault, and PR-workflow rules in the router)
   - **Proactive capture level** — `conservative` (decisions/contracts only) /
     `balanced` (+ lessons and sources, recommended) / `aggressive` (+ any new
     concept)
   - **Language** (`en` or `pt-BR`)
   Vault root (`docs/brain`) and initial areas are sensible defaults — state
   them in your summary as confirmable, don't ask.
2. **Write `brain.config.toml`** at the repo root from
   `${CLAUDE_PLUGIN_ROOT}/brain.config.example.toml`, filling in the answers.
   Record the interview for the other skills as plain keys:
   `project_mode = "existing"|"greenfield"` and `team = true|false`.
   Don't overwrite an existing config — diff and ask first.
3. **Copy the skeleton.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/vault/<language>/`
   into `<vault_root>/`, skipping any file that already exists. Preserve the empty
   dirs (`insights/`, `raw/sources/`, `knowledge/_inbox/`, `specs/`, `adrs/`) —
   they ship with `.gitkeep`; a recursive copy keeps them. Then replace the placeholders in every copied file: `{{DATE}}` with today's
   date (ISO `YYYY-MM-DD`) and `{{CAPTURE_LEVEL}}` with the chosen level (use
   the locale's word: en `conservative/balanced/aggressive`, pt-BR
   `conservador/equilibrado/agressivo`).
4. **Verify.** Grep the copied vault for residual `{{DATE}}`/`{{CAPTURE_LEVEL}}` (fail and re-render if
   any remain), then run vault_sync. The `hipocampo` package isn't vendored yet
   (that's `brain-scripts-init`), so run it from the kit:
   `PYTHONPATH=${CLAUDE_PLUGIN_ROOT} python3 -m hipocampo.validators.vault_sync`
   (use `python` if `python3` isn't on PATH). A fresh vault must pass (index
   present, no FAILs).
5. **Report** in a few lines: vault root, language, areas, files created. Point the
   user at `capture.md` (how chat becomes durable notes) and `context-budget.md`
   (index-first reads).

## Rules

- Idempotent: existing notes/config are never clobbered — surface a diff instead.
- No secrets ever get scaffolded. The vault is the user's; you only lay the skeleton.
- Next steps to suggest: `brain-router-init` (the AGENTS.md router) and
  `brain-scripts-init` (vendor the validators + git hooks).
