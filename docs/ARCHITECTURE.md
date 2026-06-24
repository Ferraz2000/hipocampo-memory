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
   (`capture`, `search`, `recall`, `reflect`, `discovery`, `spec`, `challenge`,
   `discover-standards`, `garden`, `archive-closed`, `audit`, `weekly`, `promote`,
   `postmortem`, `implement`, `low-token`, `from-roadmap`, `execute-insight`) in the open Agent
   Skills format, plus `hooks/hooks.json` wiring the two hooks. The repo root is the plugin root
   (`.claude-plugin/plugin.json` with `skills`/`hooks` path keys) so skills can
   reach `templates/` and the package.

## Data flow

```
scaffold:  brain-init ──▶ <vault>/ + brain.config.toml
           brain-scripts-init ──▶ vendored hipocampo/ + .githooks + CI

use:       capture (write-gated) ──▶ knowledge/insights/raw + index + log
           search / challenge / discovery ──▶ search (BM25/FTS5)
           Stop hook ──▶ capture-sweep ──▶ knowledge/_inbox  ──(triage via /capture)──▶ knowledge/

govern:    pre-commit ──▶ gate(pre_commit) ──▶ feature_doc_sync (sensitive code w/o its doc)
           pre-push / CI ──▶ gate(pre_push|ci) ──▶ preflight (all validators)
           SessionStart ──▶ git-derived briefing (the one sanctioned auto-load)
```

The git hooks and CI call `hipocampo.gate`, which reads `[enforcement]` and
applies the configured mode per point — `block` (fail the op), `warn` (surface
findings, never block), or `off` (skip). Defaults are `block` everywhere
(backward compatible); a low-friction setup is `warn` locally + `block` in CI.
The validators always report truthfully; the gate decides whether that blocks.

## Retrieval — target state (Phases 11–12, planned)

> **Planned, not yet shipped.** Today: SessionStart briefing + BM25/FTS5 search.
> This is where semi-automatic capture (Phase 12, Onda 1) and the optional
> semantic tier (Phase 11, Onda 2) land. One engine, three entry points, markdown
> always the truth.

```
  capture (Phase 12): agent drafts @SessionEnd ─▶ human approves ─▶ files note
                                  │
                                  ▼
                vault markdown  (SOURCE OF TRUTH)
                knowledge/index.md  (pointers, not content)
                                  │
                                  │  reindex  (derived, disposable)
                                  ▼
                .brain-cache/index.db   (gitignored, rebuildable)
                  notes_fts  (FTS5 / BM25)         ◀── always
                  notes_vec  (sqlite-vec / vector) ◀── only if [semantic]
                                  │
                                  ▼
      ┌─────────────  search engine (one path, tier-aware)  ─────────────┐
      │   query → BM25  +  [vector]  →  RRF fusion  →  ranked pointers     │
      └────────────────────────────┬─────────────────────────────────────┘
                                   │  served by 3 entry points
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
        1. Preload           2. Recall skill       3. Manual
        (SessionStart)       (agent, mid-task)     (/search, you)
        deterministic        agent's own query     on demand
```

**The engine (one code path, tier-aware).** Every search — whoever triggered it —
runs the same path: BM25 (FTS5) always; if `[semantic]` is installed the query is
also embedded (`model2vec`, CPU) and matched against `notes_vec` (`sqlite-vec`),
and the two rankings fuse via RRF. Empty vec-hits (core, no extra) ⇒ RRF
degenerates to pure BM25 — no branching, no second code path. The engine returns
**pointers + excerpts with source metadata**, never bulk content (index-first /
context-rot defense).

**Three entry points (who triggers):**

| Surface | When | Decides | Size |
|---|---|---|---|
| Preload briefing | SessionStart hook | nobody (automatic) | lean (`low-token`) |
| Recall skill | mid-task | the agent (own query) | only what's needed |
| Manual `/search` | on demand | you | as asked |

All three call the same engine; only the trigger and the destination (agent
context vs. your terminal) differ. The `AGENTS.md` router cue is what makes the
agent actually fire the recall skill ("recall before asking the user about past
decisions") — the deterministic preload + agent-decided recall split mirrors the
2026 `PreloadMemoryTool` / `LoadMemoryTool` pattern.

**Tier-invariant.** Same source (markdown), same index (`.brain-cache/index.db`),
same engine, same three surfaces. The only variable is whether `notes_vec` exists;
`[semantic]` is a pure additive upgrade — a second hit-list, nothing else — so the
core still runs headless with zero deps.

## Requirements (per machine, by tier)

The core is **vendored** (`hipocampo/` is committed), so it needs **no
`pip install`** — only the optional semantic tier does.

| Tier | Per machine | Pulls | Status |
|------|-------------|-------|--------|
| **Core + capture** | Python 3.11+ (stdlib `tomllib`), git, an agent CLI (Claude Code / Codex / Gemini) | nothing — package vendored, `sqlite3` is stdlib | ✅ shipped |
| **`[semantic]`** | the above **+** `pip install hipocampo[semantic]` | `numpy` + `model2vec` (+ a ~15–30 MB model blob, downloaded once) + `sqlite-vec` (native loadable extension) | ⬜ Phase 11 |

**The one implicit requirement for `[semantic]`:** the machine's Python `sqlite3`
must have `enable_load_extension` available (some macOS system Pythons / minimal
Docker images disable it). If absent, `sqlite-vec` can't load and search degrades
to BM25 — no crash, just no vectors on that machine. FTS5 behaves the same: present
in most Python SQLite builds; absent ⇒ pure-BM25 fallback (zero install either way).

**Never required, any tier:** no daemon/server, no Docker, no external vector DB,
no API key (the `[llm]` tier is separate and opt-in), no GPU/Ollama, no runtime
internet (after the model is cached). Everything stays in-process and embeddable.

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

## Threat model (honest limits)

The **write-gate is protocol-enforced, not technically enforced**: skills instruct
the agent to propose before writing durable memory; nothing physically stops a
misbehaving agent from writing to `knowledge/` directly. The validators catch
*drift* (missing index entries, broken provenance, off-vocabulary status), and the
capture sweep redacts secret-shaped strings — but the model assumes a
**cooperating agent + human review via git diff**. If you need hard enforcement,
put the vault behind a protected branch and review PRs.

## Distribution

One repo, one portable core, thin per-agent adapters. The skills (open Agent
Skills format) are read **natively** by Claude Code, Codex, and Gemini; the
`AGENTS.md` router, the zero-dep Python package, and the git-hook/CI templates run
anywhere. The two session automations are wired to each agent's native hook system:
Claude Code via the plugin's `hooks.json` (`SessionStart`/`Stop`), Codex via
`.codex/hooks.json`, Gemini via `.gemini/settings.json` (`SessionStart`/
`SessionEnd`) — installed from `templates/hooks/` by `brain-scripts-init`. The
hook logic (`hipocampo/hooks/`) is identical across agents; only the wiring and
the output envelope (`--format json` → `additionalContext`) differ. See the
[cross-agent matrix](../README.md#cross-agent-support) and [PUBLISHING](../PUBLISHING.md).
