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
| 4 | Generator skills (`brain-init`, `brain-router-init`, `brain-scripts-init`, `brain-update`) + workflow skills (`capture`, `discovery`, `spec`, `search`) + hooks (SessionStart briefing, Stop capture-sweep) + plugin/marketplace | ✅ done |
| 5 | Vault templates + limiter docs (`capture.md`, `context-budget.md`, `README.md`, `knowledge/index.md`, `log.md`, note templates) — **bilingual EN + pt-BR** | ✅ done |
| 6 | Improvements from research (below) as incremental PRs | ✅ done (#7 deferred by design) |
| 7 | Dogfood: Go repo (mechanical, 8/8) + Node repo (live agent-walkthrough of the corrected skills, all green) — found & fixed real prose/hook gaps (v0.2.1). Origin-project-as-consumer still pending (production, on owner confirmation) | 🟡 dogfood done; migration pending |

## Validation

- **Go repo (mechanical, me):** 8/8 — scaffold, doc-sync gate, search, capture,
  hooks, router-lint. EXECUTED.
- **Node repo (live agent-walkthrough of corrected skills):** all green. EXECUTED.
- **Round 4 (v0.2.4, executed live):** brain-update 3-way (17 auto-updated, 1
  local-mod flagged), brain-router-init full (lint-clean router + CLAUDE.md +
  USER.md seed), discovery (insight filed, vault green), pt-BR scaffold
  (vault_sync green), FTS5-absent fallback (mocked, unit), **CI in a real GitHub
  consumer repo** — defense-in-depth proven: pre-commit blocks → --no-verify →
  pre-push blocks → --no-verify → Actions run FAILS on the missing doc
  (GITHUB_EVENT_BEFORE mapping works). **Real `claude plugin install`** caught
  `author` needing to be an object (fixed) and now installs cleanly.
- **Independent audit (separate model, v0.2.1):** executed every path; confirmed
  zero-dep, config-driven, doc-sync gate, search fallback, hooks. Found 2 major +
  6 minor issues → all addressed in **v0.2.3**: `.gitignore` scaffolding (cache no
  longer committed), secret redaction in the capture sweep, doc_sync `docs` globs,
  recursive index check + missing-vault warn, TOML error handling, configurable
  doc_links excludes, hooks.json interpreter fallback, search no longer returns the
  index hub, CI base-ref mapping.

## Phase 8 — consumer-feedback ports (v0.5.0)

- `normalize` — vocabulary FIXER (vault_sync flags; this repairs): grade synonyms
  (PT/EN) -> low/medium/high + `[area_aliases]` -> canonical; spec untouched.
- `canary` — adversarial self-test of the gates against the consumer's REAL
  brain.config.toml (7 scenarios, temp fixtures, real tree untouched). Proven
  7/7 against the origin project's config.
- `hooks/ensure_githooks` — SessionStart hook setting `core.hooksPath .githooks`
  (idempotent; without it the doc-sync gate silently never runs in fresh/web
  containers). Wired first in plugin hooks.json.

## Phase 9 — real cross-agent (Codex + Gemini)

Research (primary sources, late 2025/early 2026) confirmed the portable core was
already cross-agent and the rest had native equivalents:

- **Skills** are read natively by all three CLIs (Claude Code, Codex
  `.agents/skills`, Gemini `.gemini/skills`) — `npx skills` is just an installer,
  no wrappers/MCP.
- **Router** `AGENTS.md`: Codex auto-discovers; Gemini needs `context.fileName`;
  Claude keeps the `CLAUDE.md → @AGENTS.md` bridge.
- **Hooks**: Codex (`SessionStart`/`Stop`) and Gemini (`SessionStart`/`SessionEnd`)
  both ship full hook frameworks with `additionalContext` injection and
  `transcript_path`. Ported the two automations natively:
  - `session_start --format json` emits `hookSpecificOutput.additionalContext`
    (accepted by all three; plain stdout kept as default/Claude path).
  - `capture_sweep` reads each agent's transcript shape (Gemini `parts`, Claude/
    Codex `content`, `message`-wrapped) and tolerates Codex's unstable format;
    skips Gemini `reason == "clear"`.
  - New `templates/hooks/{codex,gemini}/` wiring; `brain-scripts-init` installs it.
- **Persona** path is config-driven (`[memory] persona_file`); Codex/Gemini point
  it from `AGENTS.md` instead of Claude's auto-loaded `.claude/rules/`.
- ⚠️ Codex hooks experimental; Gemini key drift `contextFileName`→`context.fileName`.

## Phase 10 — configurable enforcement (block / warn / off)

The doc-sync gate blocked commits/pushes unconditionally; not every workflow is
100% vibe-code, so the blocking is now a per-point policy in `brain.config.toml`:

- `[enforcement]` with `pre_commit` / `pre_push` / `ci`, each `block` | `warn` |
  `off`. Defaults `block` everywhere (backward compatible).
- New `hipocampo/gate.py` is the single policy point: the git hooks + CI call it
  (not the validators directly), it reads the mode and translates the exit code
  (`block` propagates, `warn` surfaces then exits 0, `off` skips). Validators stay
  truthful (used unchanged by `canary`/standalone).
- `templates/githooks/{pre-commit,pre-push}` + `templates/ci/agent-docs.yml` now
  invoke `hipocampo.gate`. `brain-scripts-init` asks the level and recommends
  **warn local + block CI** (never stuck mid-task; drift still can't merge).

## Phase 11 — tiered capabilities (optional dependencies) ⬜ planned · **Onda 2**

Keep the core stdlib-only; add power as opt-in **extras** so the "runs in any
container/CI" promise never breaks. Supersedes deferred improvement #7. **Build
after Phase 12** — semantic recall over an empty vault is wasted; fill it first.

**Packaging.** One repo, one package, `[project.optional-dependencies]`:

- core `pip install hipocampo` → zero deps (invariant unchanged).
- `hipocampo[semantic]` → `sqlite-vec` + `model2vec` + `numpy`.
- `[graph]` (`graphiti-core`) / `[llm]` (BYO key, no fixed SDK) — documented, not built.

**Invariants.** The core test suite must stay green with **no extra installed**; a
backend that can't import (or whose SQLite forbids `load_extension`) degrades to
BM25 — never crashes. Extras are additive, never required. Markdown stays the
source of truth; vectors live in the disposable `.brain-cache/` index and rebuild
from `.md` via `reindex`. No daemon: `sqlite-vec` is in-process, `model2vec`
embeddings are local/CPU.

### Tier `[semantic]` — three pieces, not one

Grounding (2026 market): the field converged on "memory as a tool the agent
calls" + a small deterministic preload (Google ADK's `LoadMemoryTool` +
`PreloadMemoryTool` split; AgeMem treats recall as a callable op). Benchmark says
hybrid BM25+vec ≈ pure vector DB (95.2 vs 96.6 on LongMemEval-S), so an embeddable
engine beats a server. B is therefore three pieces:

1. **Semantic backend** — `model2vec` static embeddings (CPU, ~30MB model) into a
   `sqlite-vec` `vec0` table inside the same `.brain-cache/index.db` as FTS5;
   results fused with the existing RRF. Empty vec-hits ⇒ degenerates to today's
   BM25, so **one code path serves both tiers**.
2. **Agent-callable recall skill** — the `LoadMemoryTool` half: the agent composes
   its own query mid-task and pulls only what it needs (lower-noise than
   always-inject). The SessionStart briefing stays the small `PreloadMemoryTool`
   half (keep it `low-token`).
3. **Router cue in `AGENTS.md`** — the wiring that makes the agent actually fire
   the recall skill ("before asking the user about past decisions, recall first").
   hipocampo's router already *is* this surface; B only adds the cue.

Without (2)+(3) the engine only serves manual search — the agent never uses it.

**Cost (honest — why opt-in).** `[semantic]` pulls `numpy` + a model blob + the
`sqlite-vec` native loadable extension (some Python/SQLite builds disable
extension loading) — real weight, hence behind the extra. Buys ~+9 pts recall
(86→95), concentrated in fuzzy/paraphrased queries (preferences 60→83); exact-term
lookups already ~86% on BM25 alone.

**Depends on capture density.** B's value scales with how full the vault is — pair
with semi-automatic capture (agent drafts at SessionEnd, human approves) or the
semantic engine just searches an empty vault.

## Phase 12 — semi-automatic capture 🟡 in progress · **Onda 1 (build first)**

Closes the one real hole in the human-write-gate model: 100% manual `/capture`
leaves the vault sparse (nobody remembers to file), and an empty vault makes
Phase 11's recall worthless. Fix: the agent **drafts**, the human **approves** —
keep the gate, kill the emptiness. Grounded in 2026 "proactive memory extraction"
(extract what's worth keeping; don't summarize everything).

**Flow:**

1. **SessionEnd hook** → agent scans the session and writes capture **candidates**
   (decisions, learnings, gotchas) to `.brain-cache/pending-capture.md`. Never
   touches the vault — staging is disposable. Evolves the shipped `capture_sweep`
   hook (already reads each agent's transcript), so no new machinery.
2. **SessionStart** (or `/capture --review`) → show candidates; human accepts
   (enter), edits, or drops each. Safe default: nothing reaches the vault without
   a yes.
3. **Approved** → markdown notes in the vault (git-versioned), area/status
   vocabulary from `brain.config.toml`. Dropped → gone.

**Config** (`brain.config.toml`):

```toml
[capture.auto]
mode = "draft"      # draft | off  (never "commit" — human gate is invariant)
max_candidates = 7  # AgeMem-style: cap noise, discard near-duplicates
```

**Invariants:**

- Nothing enters durable memory without human approval (the differentiator holds).
- Core, stdlib-only: SessionEnd hook + staging file + the existing `/capture`.
  Zero dependency — reuses the `capture_sweep` hook already shipped.
- Pairs with Phase 11: Onda 1 fills the vault, Onda 2 makes it findable by concept.

**Landed (increment 1):** `capture_sweep` now branches on `[capture.auto] mode`
(`inbox` legacy default | `draft` | `off`). `draft` stages checkbox candidates in
the disposable `.brain-cache/pending-capture.md` (never the vault), dedups per
session, and the SessionStart briefing surfaces them; `/capture --review` triages.
`brain-scripts-init` recommends `draft` for new setups. Tests green (127).
**Next:** richer agent-reasoned drafting (beyond regex triggers) + the review-loop
ergonomics.

## Script port status (origin → `hipocampo/`)

| Origin script | Generic % | Target | Status |
|---------------|-----------|--------|--------|
| `vault_tools.py` (1078L) | ~70% | `hipocampo/vault.py` (+ `views.py`) | ✅ (split: `vault.py` governance + `views.py` materialization) |
| `search-vault.py` (216L) | ~90% | `hipocampo/search.py` | ✅ |
| `vault_index.py` (292L) | ~90% | `hipocampo/index.py` | ✅ |
| `preflight.py` (47L) | ~80% | `hipocampo/preflight.py` | ✅ |
| `inbox_decay.py` (100L) | ~85% | `hipocampo/inbox_decay.py` | ✅ |
| `parse_frontmatter` (from vault_tools) | 100% | `hipocampo/frontmatter.py` | ✅ |
| `validate-doc-links.py` | ~90% | `hipocampo/validators/doc_links.py` | ✅ |
| `validate-feature-doc-sync.py` | ~50% (AREA_RULES → config `doc_sync`) | `hipocampo/validators/feature_doc_sync.py` | ✅ |
| `validate-vault-sync.py` (generic subset) | ~60% | `hipocampo/validators/vault_sync.py` | ✅ |
| `generate-vault-views.py` (DQL→markdown) | ~70% | `hipocampo/views.py` | ✅ (v0.4.0; 9/9 table parity vs origin `_generated/`) |

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
- ⬜ #7 optional local semantic search → **promoted to Phase 11** (tiered extras: `hipocampo[semantic]` = `sqlite-vec` + `model2vec`, three-piece design — backend + recall skill + router cue). Still opt-in to keep the core zero-dep.
- ✅ Phase 5b: `views.py` (DQL→markdown materialized views) + opt-in `views_fresh` validator (v0.4.0).
