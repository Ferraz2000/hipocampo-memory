---
name: brain-init
description: Scaffold a hipocampo memory vault into the current project — creates brain.config.toml and the docs/brain skeleton (knowledge/index, capture.md, context-budget.md, note templates). Use when setting up agent memory in a repo that doesn't have a vault yet, or when the user says "init the brain", "set up the vault", "brain-init".
---

# brain-init — scaffold the vault

Create a durable, git-versioned, human-gated memory vault in this repo. Idempotent:
never overwrite an existing `.md`.

## Steps

1. **Detect existing setup.** If `brain.config.toml` already exists, read it and
   reuse its `vault_root`/`language`. Otherwise gather, via one `AskUserQuestion`:
   - language (`en` or `pt-BR`),
   - vault root (default `docs/brain`),
   - initial `areas` (default `["meta", "architecture", "product", "testing"]`).
2. **Write `brain.config.toml`** at the repo root from
   `${CLAUDE_PLUGIN_ROOT}/brain.config.example.toml`, filling in the answers.
   Don't overwrite an existing config — diff and ask first.
3. **Copy the skeleton.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/vault/<language>/`
   into `<vault_root>/`, skipping any file that already exists. Replace the
   `{{DATE}}` placeholder with today's date (ISO `YYYY-MM-DD`) in every copied file.
4. **Verify.** Run `python3 -m hipocampo.validators.vault_sync` — a fresh vault must
   pass (index present, no FAILs).
5. **Report** in a few lines: vault root, language, areas, files created. Point the
   user at `capture.md` (how chat becomes durable notes) and `context-budget.md`
   (index-first reads).

## Rules

- Idempotent: existing notes/config are never clobbered — surface a diff instead.
- No secrets ever get scaffolded. The vault is the user's; you only lay the skeleton.
- Next steps to suggest: `brain-router-init` (the AGENTS.md router) and
  `brain-scripts-init` (vendor the validators + git hooks).
