# hipocampo

🌐 [Português](README.pt-BR.md) · **English**

**Persistent, git-versioned, human-gated memory for coding agents.** Your agents
(Claude Code, Codex, Gemini) stop forgetting between sessions and stop letting
docs rot — in any project, any language.

> *Hipocampo* (hippocampus) is the brain region that consolidates short-term
> memory into long-term memory. The kit does the same: raw captures land in an
> `_inbox/`, and a write-gated pipeline turns them into a curated, auditable
> `knowledge/` base that lives in your repo and compounds over time.

**Status: v0.12.0 — usable.** 216 tests, CI green, validated end-to-end including a
production project as first consumer, plus an opt-in semantic tier verified with
the deps installed and the kit dogfooding its own memory ([details](PLAN.md)).

## Quickstart (2 minutes)

```sh
/plugin marketplace add Ferraz2000/hipocampo-memory     # Claude Code (skills + hooks)
/plugin install hipocampo@hipocampo
# or cross-agent (Claude Code / Codex / Gemini) — skills install natively:
npx skills add Ferraz2000/hipocampo-memory
```

On Codex and Gemini the skills are read natively (no wrapper); `brain-scripts-init`
also wires the session hooks for them. See [Cross-agent support](#cross-agent-support).

Then say `/brain-init` in your project. **The agent does the setup** — it asks
you three questions (language, where the vault lives, initial areas), generates
the config, and scaffolds the vault. From there, day-to-day is just talking:

```
/capture <something>    # "remember this decision" → becomes a reviewable note
/search <terms>         # "what do we know about X?"
```

That's all you need to start. Everything else is optional and the agent runs it
for you — see [the full toolbox](#the-full-toolbox).

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
  Update one of: docs/architecture/persistence.md
$ git add docs/architecture/persistence.md && git commit ...   # passes
```

And memory becomes a **reviewable diff**, not a black box:

```diff
+ docs/brain/knowledge/architecture/error-style.md   # /capture wrote this
+ docs/brain/knowledge/index.md                       # +1 index line
```

Agent proposes → you approve → it lands in git. Validators keep it honest;
`python -m hipocampo.canary` proves the gates bite against *your* setup.

## How it works

One principle: **the human curates by talking; the agent does the bookkeeping.**

| Layer | Where | Truth? |
|------|-------|--------|
| Rules (how to work here) | `AGENTS.md` / `.claude/rules/` | yes |
| Working memory (in flight) | git-derived session briefing | no (cockpit) |
| Durable knowledge | `knowledge/` + official docs | yes |
| Proposals ("should we?") | `insights/` (scored) | not yet |
| Provenance | `raw/sources/` (immutable) | anchor |

Reads are **index-first**: the agent reads a cheap `knowledge/index.md` and
loads only the relevant pages — never the whole vault (context-rot defense).
Writes go through a **human write-gate** (`/capture`): the agent proposes, you
approve, the agent files and reports.

## What lands in your repo

`/brain-init` + `/brain-scripts-init` add, and the agent maintains:

```
brain.config.toml     # all project-specific settings (generated, not hand-written)
docs/brain/           # the vault: knowledge/, insights/, raw/sources/, templates
hipocampo/            # vendored zero-dependency scripts (search, gates, hooks)
.githooks/            # pre-commit doc-sync gate + pre-push preflight
.github/workflows/    # optional: same gates in CI
```

Plain markdown + stdlib Python. No daemon, no database, no pip installs —
delete the folders and it's gone.

## The full toolbox

22 skills, grouped — **you don't memorize these; the agent picks them from what
you say.** Adopt incrementally:

- **Setup (once):** `brain-init`, `brain-router-init`, `brain-scripts-init`, `brain-update`.
- **Daily:** `capture`, `search`, `recall` (agent pulls memory mid-task), `low-token` (lean mode).
- **Thinking:** `challenge` (confront a decision with past reversals), `reflect` (bounded critique→revise loop, memory-seeded), `discovery`, `spec`, `discover-standards`.
- **Insight lifecycle:** `from-roadmap` → `promote` → `implement` / `execute-insight` → `weekly` / `postmortem` / `audit`.
- **Maintenance:** `garden`, `archive-closed` (+ the `normalize` fixer and the `canary` self-test).

Plus two session hooks (a session-start git briefing; a session-end capture-sweep
with secret redaction) — wired per agent — and six config-driven validators run
by `preflight`.

## Cross-agent support

One kit, thin per-agent adapters. The portable core (the 22 SKILL.md skills, the
`AGENTS.md` router, the zero-dep Python package, git hooks + CI) runs anywhere;
the session automations are wired to each agent's native hook system.

| Capability | Claude Code | Codex CLI | Gemini CLI |
|------------|-------------|-----------|------------|
| Skills (SKILL.md) | native | native (`.agents/skills`) | native (`.gemini/skills`) |
| Router (`AGENTS.md`) | via `CLAUDE.md → @AGENTS.md` | auto-discovered | set `context.fileName` in `.gemini/settings.json` |
| Session-start briefing | `SessionStart` hook | `SessionStart` hook | `SessionStart` hook |
| Session-end capture-sweep | `SessionEnd` hook | `Stop` hook | `SessionEnd` hook |
| Persona memory | `.claude/rules/USER.md` (auto-load) | file referenced from `AGENTS.md` | file referenced from `AGENTS.md` |
| Path-scoped rules | native (`.claude/rules/*.md` `paths:`) | fold into `AGENTS.md` | fold into `AGENTS.md` |
| Doc-sync gate, search, validators | ✅ (vendored Python) | ✅ | ✅ |

Notes: Codex hooks are **experimental** (the transcript format isn't stable — the
sweep degrades gracefully). Gemini's router key is `context.fileName` (older
builds: `contextFileName`). The persona path is configurable via
`[memory] persona_file` in `brain.config.toml`.

## Configuration

Everything project-specific lives in **`brain.config.toml`** at the repo root.
**You don't write it by hand** — `/brain-init` generates it from three answers,
and you evolve it by asking the agent ("add a doc-sync rule for `src/api/`",
"raise the decay window to 60 days"). The full schema, for auditing or manual
edits: [`brain.config.example.toml`](brain.config.example.toml).

**Don't want the gate blocking you?** Enforcement is configurable per point
(`[enforcement]`): `block` (fail), `warn` (surface findings, never block), or
`off`. `brain-scripts-init` asks and recommends **warn locally + block in CI** —
you're never stuck mid-task, but drift still can't merge.

## Why this and not a memory framework

The 2025–2026 state of the art converged on **markdown as the source of truth +
an optional derived index** (Anthropic auto-memory, Letta Code's MemFS,
basic-memory — independently). DB-backed memory trades away git-diff
auditability. hipocampo adds the piece no published framework ships well:
**governance** — a human write-gate, frontmatter-as-truth, and a per-commit
doc-sync gate.

> **Teams:** the write-gate is protocol-enforced (a cooperating agent + git
> review). For hard enforcement, put the vault behind a **protected branch with
> required PR review** — see the [threat model](docs/ARCHITECTURE.md#threat-model-honest-limits).

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how it works (consolidated).
- [PLAN.md](PLAN.md) — phases, decisions, validation history.
- [PUBLISHING.md](PUBLISHING.md) — releases + community-marketplace submission.
- [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup, kit internals layout, non-negotiables.

## License

MIT — see [`LICENSE`](LICENSE).
