# hipocampo

🌐 [Português](README.pt-BR.md) · **English**

**Persistent, git-versioned, human-gated memory for coding agents.** A reusable
kit that scaffolds a knowledge vault + skills + hooks + validation scripts into
**any project, any language** — so your agents (Claude Code, Codex, Gemini)
stop forgetting between sessions and stop relearning the same things.

> *Hipocampo* (hippocampus) is the brain region that consolidates short-term
> memory into long-term memory. That is exactly what this kit does: a
> write-gated pipeline that moves an `_inbox/` of raw captures into a curated,
> auditable `knowledge/` base that lives in your repo and compounds over time.

**Status: v0.6.x — usable.** 94 tests, CI green, validated end-to-end five times
(mechanical dogfood in Go, a live agent walkthrough in Node, an independent
adversarial audit, a post-fix re-audit with real CI + real plugin install, and a
production project migrated as the first consumer). See [`PLAN.md`](PLAN.md).

## Quickstart (2 minutes)

```sh
/plugin marketplace add Ferraz2000/hipocampo     # Claude Code (skills + hooks)
/plugin install hipocampo@hipocampo
# or cross-agent (Claude Code / Codex / Gemini), skills only:
npx skills add Ferraz2000/hipocampo
```

Then, in your project, you only need **three skills** to start:

```
/brain-init             # scaffold the vault + brain.config.toml
/registra <something>   # capture a decision/lesson as a reviewable note
/busca <terms>          # search what the brain already knows
```

Everything else (router generation, vendored gates, the insight lifecycle) is
there when you want it — see [the full toolbox](#the-full-toolbox). Don't learn
it up front.

## What it looks like (before / after)

**Before** — the agent changes a sensitive area; the doc silently rots:

```sh
$ git commit -m "feat: change persistence model"
[main abc1234] feat: change persistence model      # doc drift starts here
```

**After** — the doc-sync gate (pre-commit → pre-push → CI, same rule) blocks it:

```sh
$ git commit -m "feat: change persistence model"
feature-doc-sync validation FAILED
  Sensitive area changed without its doc update: persistence
  Files:  src/app/migrations/0042_split.sql
  Update one of: docs/architecture/persistence.md
$ git add docs/architecture/persistence.md && git commit ...   # passes
```

And memory becomes a **reviewable diff**, not a black box:

```diff
+ docs/brain/knowledge/architecture/error-style.md   # /registra wrote this
+ docs/brain/knowledge/index.md                       # +1 index line
+ docs/brain/log.md                                   # +1 dated log line
```

Agent proposes → you approve → it lands in git → `vault_sync` keeps it honest
(provenance, index, vocabulary). `python -m hipocampo.canary` proves the gates
bite against *your* config (7 adversarial scenarios).

## Why this and not a memory framework

The 2025–2026 state of the art converged on **markdown as the source of truth +
an optional derived index** (Anthropic auto-memory, Letta Code's MemFS,
OpenClaw/memsearch, basic-memory — independently). DB-backed memory
(mem0/Zep/claude-flow) trades away git-diff auditability and ships contested
benchmarks. hipocampo's bet is the durable one, plus the piece no published
framework ships well: **governance** — a human write-gate, frontmatter-as-truth,
and a per-commit doc-sync gate.

> **Teams:** the write-gate is protocol-enforced (a cooperating agent + git
> review). For hard enforcement, put the vault behind a **protected branch with
> required PR review** — see the [threat model](docs/ARCHITECTURE.md#threat-model-honest-limits).

## How it works (the layers)

| Layer | Where | What | Truth? |
|------|-------|------|--------|
| Procedural | `AGENTS.md` / `CLAUDE.md` / `.claude/rules/` | how the agent should work here | yes (rules) |
| Working memory | roadmap / inbox (git-derived briefing) | what's in flight now | no (cockpit) |
| Semantic | `knowledge/` + official docs | durable concepts & decisions | yes (durable) |
| Proposals | `insights/` | scored "should we?" candidates | not yet |
| Provenance | `raw/sources/` | immutable ingested sources | no (lastro) |

Reads are **index-first** (Karpathy LLM-wiki): the agent reads a cheap
`knowledge/index.md`, loads only the relevant pages, never bulk-reads the vault
(context-rot defense). Writes go through a **human write-gate** (`/registra`):
the agent proposes, you approve, the agent files and reports.

## The full toolbox

20 skills (+3 pt-BR aliases), grouped — adopt incrementally:

- **Setup (once):** `brain-init`, `brain-router-init`, `brain-scripts-init`,
  `brain-update`.
- **Daily:** `capture` (pt-BR alias `/registra`), `search` (alias `/busca`), `low-token` (lean mode).
- **Thinking:** `challenge` (confront a decision with past reversals),
  `discovery` (bounded broad read), `spec`, `discover-standards`.
- **Insight lifecycle:** `from-roadmap` → `promote` → `implement` /
  `execute-insight` → `weekly` / `postmortem` / `audit` (alias `/audita`).
- **Maintenance:** `garden`, `archive-closed` (+ `python -m hipocampo.normalize`
  fixer and the `canary` self-test).

Plus two hooks (SessionStart git briefing, Stop capture-sweep with secret
redaction) and nine config-driven validators run by `preflight`.

## Configuration

Everything project-specific lives in **`brain.config.toml`** at the repo root —
vault location, area/status vocabulary, doc-sync rules, decay window, capture
triggers, language. Scripts read this config; nothing is hardcoded. See
[`brain.config.example.toml`](brain.config.example.toml).

## Repo layout

```
hipocampo/                 # the python package (zero-dep, stdlib only)
  config.py                # loads brain.config.toml + defaults
  frontmatter.py           # YAML-ish frontmatter parser
  search.py                # pure-BM25 keyword search over the vault
  index.py                 # optional SQLite FTS5 index + RRF graph fusion
  views.py                 # dataview DQL -> static markdown mirrors
  normalize.py             # vocabulary fixer (vault_sync flags; this repairs)
  canary.py                # adversarial self-test of the gates vs YOUR config
  inbox_decay.py           # expire stale capture-sweeps
  globs.py                 # gitignore-style ** path matching
  vault.py                 # markdown page model (frontmatter-as-truth)
  preflight.py             # run all configured validators (hook + CI entry)
  validators/              # doc_links, feature_doc_sync (doc-sync gate),
                           # vault_sync, views_fresh, router_lint, catalog_sync
  hooks/                   # session_start, capture_sweep, ensure_githooks
  tests/                   # stdlib unittest (94)
plugin/                    # Claude Code plugin (20 skills + hooks.json)
templates/                 # scaffolded into target repos
  githooks/                # pre-commit (doc-sync gate) + pre-push (preflight)
  ci/                      # agent-docs workflow
  vault/{en,pt-BR}/        # the docs/brain skeleton (limiters + note templates)
brain.config.example.toml  # documented config schema
PLAN.md                    # extraction roadmap + port status
```

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how it works (consolidated).
- [PLAN.md](PLAN.md) — phases, decisions, port status.
- [PUBLISHING.md](PUBLISHING.md) — releases + community-marketplace submission.
- [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup + non-negotiables.

## License

MIT — see [`LICENSE`](LICENSE).
