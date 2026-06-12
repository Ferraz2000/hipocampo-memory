# hipocampo

**Persistent, git-versioned, human-gated memory for coding agents.** A reusable
kit that scaffolds a knowledge vault + skills + hooks + validation scripts into
**any project, any language** — so your agents (Claude Code, Codex, Gemini)
stop forgetting between sessions and stop relearning the same things.

> *Hipocampo* (hippocampus) is the brain region that consolidates short-term
> memory into long-term memory. That is exactly what this kit does: a
> write-gated pipeline that moves an `_inbox/` of raw captures into a curated,
> auditable `knowledge/` base that lives in your repo and compounds over time.

> ⚠️ **Status: early (v0.0.x), under active extraction.** The kit is being
> extracted and generalized from a battle-tested private system. See
> [`PLAN.md`](PLAN.md) for what's shipped vs pending.

## Why this and not a memory framework

The 2025–2026 state of the art converged on **markdown as the source of truth +
an optional derived index** (Anthropic auto-memory, Letta Code's MemFS,
OpenClaw/memsearch, basic-memory — independently). DB-backed memory
(mem0/Zep/claude-flow) trades away git-diff auditability and ships contested
benchmarks. hipocampo's bet is the durable one, plus the piece no published
framework ships well: **governance** — a human write-gate, frontmatter-as-truth,
and a per-commit doc-sync gate.

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

## Install (planned)

Two tracks from one repo:

```sh
# cross-agent skills (Claude Code, Codex, Gemini) — once published
npx skills add Ferraz2000/hipocampo

# Claude Code plugin (skills + hooks + scripts) — once published
/plugin marketplace add Ferraz2000/hipocampo
/plugin install hipocampo@hipocampo
```

Then scaffold a vault into the current project:

```
/brain-init          # generate the vault + brain.config.toml
/brain-router-init   # generate AGENTS.md router for this language/stack
/brain-scripts-init  # vendor the validation scripts + git hooks + CI
```

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
  inbox_decay.py           # expire stale capture-sweeps
  globs.py                 # gitignore-style ** path matching
  vault.py                 # markdown page model (frontmatter-as-truth)
  preflight.py             # run all configured validators (hook + CI entry)
  validators/              # doc_links, feature_doc_sync (doc-sync gate), vault_sync
  tests/                   # stdlib unittest
plugin/                    # Claude Code plugin (skills, hooks) — WIP
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
