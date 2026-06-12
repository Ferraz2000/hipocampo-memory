# hipocampo — extraction plan & port status

This repo extracts and generalizes a private, battle-tested agent-memory system
into a reusable kit. Source-of-record for the design decisions is the captured
research digest and plan (private vault); this file is the public, living
roadmap.

## Principles (carried from the research)

- **Markdown is the source of truth**; any index/cache is derived and disposable.
- **Human write-gate**: the agent proposes captures, the human approves, the
  agent files and reports. No autonomous writes to durable memory.
- **Index-first reads** (Karpathy LLM-wiki): cheap `knowledge/index.md` →
  load only relevant pages → never bulk-read the vault (context-rot defense).
- **Frontmatter-as-truth**: dashboards/readouts are projections of frontmatter,
  never hand-curated.
- **Lean, operational router**: short `AGENTS.md` with concrete commands/paths
  (vague long instruction files measurably tax reasoning).
- **Zero runtime deps**: stdlib-only Python so it runs in any container/CI.
- **Config-driven**: all project-specifics live in `brain.config.toml`.

## Decisions (locked)

- **Name** `hipocampo`, **public**, **MIT**.
- **Config** is `brain.config.toml` (TOML via stdlib `tomllib`) — chosen over YAML
  to keep the zero-dependency promise (no PyYAML).
- **Vault default** `docs/brain/` (neutral, configurable via `vault_root`).
- **Bilingual templates: English + pt-BR.** Kit source/docs are English for reach;
  scaffolded vault content ships per-locale under `templates/vault/{en,pt-BR}/`,
  selected by the `language` key. Script logic is language-agnostic.

## Distribution (decided)

Hybrid, one git repo as source:

1. **Cross-agent skills** (Agent Skills open format) → `npx skills add` installs
   into Claude Code / Codex / Gemini.
2. **Claude Code plugin** + git marketplace → the only vehicle that carries
   hooks + `bin/` scripts + default settings.
3. **Scaffold via skill** (not cookiecutter) so bootstrap is cross-agent.

## Phases

| Phase | Deliverable | Status |
|------|-------------|--------|
| 1 | Foundation: repo skeleton, config loader, first working slice (inbox_decay) + tests | ✅ done |
| 2 | Retrieval layer: `search` (pure BM25) + `index` (FTS5 + RRF graph fusion), config-driven, with tests | ✅ done |
| 3 | Governance: `vault.py` page model + validators (`doc_links`, `feature_doc_sync` via config `doc_sync`, `vault_sync`) + config-driven `preflight` + git-hook/CI templates | ✅ done (DQL→markdown views deferred to optional 5b) |
| 4 | Generator skills (`brain-init`, `brain-router-init`, `brain-scripts-init`, `brain-update`) + workflow skills (`registra`, `discovery`, `spec`, `busca`) + hooks (SessionStart briefing, Stop capture-sweep) + plugin/marketplace | ✅ done |
| 5 | Vault templates + limiter docs (`capture.md`, `context-budget.md`, `README.md`, `knowledge/index.md`, `log.md`, note templates) — **bilingual EN + pt-BR** | ✅ done |
| 6 | Improvements from research (below) as incremental PRs | ⬜ pending |
| 7 | Dogfood on a fresh non-private project; then migrate the origin project to consume the kit | ⬜ pending |

## Script port status (origin → `hipocampo/`)

| Origin script | Generic % | Target | Status |
|---------------|-----------|--------|--------|
| `vault_tools.py` (1078L) | ~70% | `hipocampo/vault.py` (+ `views.py`) | ⬜ (Phase 3) |
| `search-vault.py` (216L) | ~90% | `hipocampo/search.py` | ✅ |
| `vault_index.py` (292L) | ~90% | `hipocampo/index.py` | ✅ |
| `preflight.py` (47L) | ~80% | `hipocampo/preflight.py` | ✅ |
| `inbox_decay.py` (100L) | ~85% | `hipocampo/inbox_decay.py` | ✅ |
| `parse_frontmatter` (from vault_tools) | 100% | `hipocampo/frontmatter.py` | ✅ |
| `validate-doc-links.py` | ~90% | `hipocampo/validators/doc_links.py` | ✅ |
| `validate-feature-doc-sync.py` | ~50% (AREA_RULES → config `doc_sync`) | `hipocampo/validators/feature_doc_sync.py` | ✅ |
| `validate-vault-sync.py` (generic subset) | ~60% | `hipocampo/validators/vault_sync.py` | ✅ |
| `generate-vault-views.py` (DQL→markdown) | ~70% | `hipocampo/views.py` | ⬜ (optional, Phase 5b) |

## Improvements (Phase 6) — some already landed during Phases 1–5

- ✅ #3 dependency graph seeds (`depends_on:`/`blocks:` in the insight template).
- ✅ #4 append-only `log.md` in the vault templates.
- ✅ #6-ish stale-sweep decay + Stop-hook consolidation (sleep-time pattern).
- ✅ #1 native auto-memory policy (guidance in `brain-scripts-init`: disable or redirect to inbox).
- ✅ #2 conditional rules via `.claude/rules/` `paths:` (guidance in `brain-router-init`).
- ✅ #8 `/challenge` skill — confront a decision with the vault's past reversals/failures.
- ✅ #9 `/discover-standards` skill — mine the code, propose conventions as candidate insights.
- ✅ #10 temporal validity (`valid_until` in the knowledge template + vault_sync warning).
- ✅ #11 router-lint validator (opt-in `router_lint`: lean AGENTS.md size cap).
- ✅ #5 `/garden` skill — lint/gardener pass (contradictions, stale, orphans, missing links).
- ✅ #6 `/archive-closed` skill — semantic compaction of terminal insights into an archive index.
- ✅ #12 recitation guidance folded into `brain-router-init` (re-state the todo at phase boundaries).
- ⬜ #7 optional local semantic search (FastEmbed + disposable SQLite) — **deferred by design**: breaks the zero-dependency promise; ship as an opt-in add-on later.
- ⬜ optional Phase 5b: `views.py` (DQL→markdown materialized views) for Obsidian dashboards.
