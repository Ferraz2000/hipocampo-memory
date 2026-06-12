# Architecture — how hipocampo works

A consolidated "how it works", complementing the [README](../README.md) (what +
install) and [PLAN](../PLAN.md) (phases + decisions).

## The bet

The 2025–2026 state of the art converged on **markdown as the source of truth +
an optional derived index** (Anthropic auto-memory, Letta Code's MemFS,
OpenClaw/memsearch, basic-memory — independently). DB-backed memory trades away
git-diff auditability. hipocampo takes the durable side, and adds the piece no
published framework ships well: **governance** — a human write-gate,
frontmatter-as-truth, and a per-commit doc-sync gate.

## Memory layers

| Layer | Where | Truth? |
|------|-------|--------|
| Procedural | `AGENTS.md` / `CLAUDE.md` / `.claude/rules/USER.md` | yes (rules) |
| Working memory | git-derived SessionStart briefing | no (cockpit) |
| Semantic | `<vault>/knowledge/` + official docs | yes (durable) |
| Proposals | `<vault>/insights/` (scored) | not yet |
| Provenance | `<vault>/raw/sources/` (immutable) | anchor |

## The four moving parts

1. **The vault** (`templates/vault/{en,pt-BR}/` → scaffolded into `<vault_root>/`):
   `knowledge/` (the wiki) with a cheap `index.md`, `insights/` (proposals),
   `raw/sources/` (immutable provenance), `knowledge/_inbox/` (auto-capture
   sweeps), `specs/`, `adrs/`, `log.md` (append-only), and the two limiter docs
   `capture.md` + `context-budget.md`.
2. **`brain.config.toml`** — every project-specific value: vault location,
   area/status vocabulary, `[[doc_sync]]` rules, decay window, capture triggers,
   language, router cap. The Python package reads this; nothing is hardcoded.
3. **The Python package** (`hipocampo/`, stdlib only):
   - `config.py` — loads `brain.config.toml` (TOML via `tomllib`), deep-merged
     over `DEFAULTS`, walk-up discovery.
   - `frontmatter.py`, `vault.py` — frontmatter-as-truth page model.
   - `search.py` + `index.py` — BM25 search with an optional SQLite FTS5 index
     (incremental, + RRF graph fusion); falls back to pure BM25 (zero-dep, runs
     headless/CI/local).
   - `validators/` — `doc_links`, `feature_doc_sync` (the doc-sync gate),
     `vault_sync` (index consistency, status/area vocab, provenance/staleness),
     `router_lint` (opt-in). `preflight.py` runs the configured set.
   - `hooks/` — `session_start` (git-derived briefing) and `capture_sweep`
     (Stop-hook sweep into the inbox). Config-driven, never block.
   - `inbox_decay.py`, `globs.py`.
4. **The plugin** (`plugin/`): generator skills (`brain-init`,
   `brain-router-init`, `brain-scripts-init`, `brain-update`) and workflow skills
   (`registra`, `busca`, `discovery`, `spec`, `challenge`, `discover-standards`,
   `garden`, `archive-closed`) in the open Agent Skills format, plus
   `hooks/hooks.json` wiring the two hooks. The repo root is the plugin root
   (`.claude-plugin/plugin.json` with `skills`/`hooks` path keys) so skills can
   reach `templates/` and the package.

## Data flow

```
scaffold:  brain-init ──▶ <vault>/ + brain.config.toml
           brain-scripts-init ──▶ vendored hipocampo/ + .githooks + CI

use:       registra (write-gated) ──▶ knowledge/insights/raw + index + log
           busca / challenge / discovery ──▶ search (BM25/FTS5)
           Stop hook ──▶ capture-sweep ──▶ knowledge/_inbox  ──(triage via /registra)──▶ knowledge/

govern:    pre-commit ──▶ feature_doc_sync (blocks sensitive code w/o its doc)
           pre-push / CI ──▶ preflight (all validators)
           SessionStart ──▶ git-derived briefing (the one sanctioned auto-load)
```

## Design principles

- **Markdown is the source of truth.** Any index/cache (`.brain-cache/`) is
  derived and disposable.
- **Human write-gate.** The agent proposes; the human approves; the agent files.
- **Index-first reads** (Karpathy LLM-wiki): read `knowledge/index.md`, load only
  relevant pages, never bulk-read (context-rot defense).
- **Frontmatter-as-truth.** Dashboards/readouts project frontmatter; never
  hand-curated.
- **Zero runtime dependencies.** stdlib-only Python so it runs in any container/CI.
- **Config-driven.** All project-specifics in `brain.config.toml`.

## Distribution

Two tracks, one repo: a Claude Code **plugin** (skills + hooks, via marketplace)
and **cross-agent skills** (Agent Skills open format, via `npx skills add`). See
[PUBLISHING](../PUBLISHING.md).
