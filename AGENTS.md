# hipocampo — agent router

Reusable agent-memory kit. This file is the entry point; keep it short and
operational (vague, long instruction files measurably tax reasoning).

## Read order

1. [`PLAN.md`](PLAN.md) — phases + port status. Read before adding code so you
   know which increment you're in.
2. The target file's module docstring.
3. [`brain.config.example.toml`](brain.config.example.toml) — the config schema
   every script reads from.

## Rules

- **Zero runtime deps.** Standard library only (TOML via `tomllib`, py3.11+).
  No PyYAML, no pip installs. This is non-negotiable: the kit must run in any
  container/CI.
- **Nothing project-specific is hardcoded.** Paths, area/status vocabulary,
  doc-sync rules, decay windows, capture triggers, language — all come from
  `brain.config.toml` via `hipocampo.config.load_config()`. If you reach for a
  string literal like `"docs/obsidian"` or a capability name, it belongs in
  config instead.
- **Markdown is the source of truth.** Any index/cache (`.brain-cache/`) is
  derived and disposable; never make it authoritative.
- **Tests are stdlib `unittest`.** Run: `python -m unittest discover -s hipocampo/tests`.
- **Keep `PLAN.md` honest.** When you finish porting a script, flip its row to
  ✅ in the same change. Don't claim done what isn't.
- Conventional Commits. Branch off `main`; PRs target `main`.

## What this kit is NOT

- Not a DB-backed memory layer. If a change needs a daemon or a vector DB to
  function, it's the wrong layer — reconsider.
- Not opinionated about the target project's language. Detection lives in the
  `brain-router-init` skill, not in the scripts.
