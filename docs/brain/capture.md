---
title: Capture — how chat becomes durable knowledge
type: protocol
area: meta
status: active
tags: [capture, second-brain, agents, protocol]
created: 2026-06-17
updated: 2026-06-17
---

# Capture — how chat becomes durable knowledge

This is the capture protocol of the second brain. It defines how a **chat
conversation** becomes a durable note **without the human editing a file**: the
human curates by talking, the agent does the bookkeeping. It is the "LLM wiki"
pattern (Karpathy) adapted into this repo.

> Companion docs: [README](README.md), [context-budget](context-budget.md)
> (read/write discipline), and the root `AGENTS.md` (global rules).

## Architecture decision

- **Model: hybrid by type.** The source of truth is split by the *nature* of the
  knowledge (table below) — not "one wiki", not "everything promoted".
- **Trigger: explicit verb + proactive agent (level `balanced`).**
- **Human write-gate.** The agent never writes on its own without an "ok" — the
  explicit verb, or you accepting a proactive offer.

## The 4 types (where a note lands)

| Type | Destination | Truth? | Example |
|---|---|---|---|
| **Source** | `raw/sources/` (immutable) | the lastro/anchor | article, transcript, paper, discussed link |
| **Concept/decision** | `knowledge/<area>/` | **yes — truth in the brain** | "how we think about onboarding", "why we deferred X" |
| **Code contract** | official docs (`docs/...`) + skills | yes (gated) | API contracts, persistence, runtime behavior |
| **Proposal** | `insights/<area>/` (scored) | not yet | "should we do X?" (impact/effort/risk) |

The distinction that's easy to miss: "this is true" ≠ "we should do this".
`knowledge/` holds conceptual truth; `insights/` holds scored proposals.

## Boundary heuristic (contract vs concept)

> **Would changing this knowledge require touching code or break a test?**
> **Yes → contract** (gated layer; triggers the doc-sync gate).
> **No → concept** (truth in the brain; goes to `knowledge/`).

Edge case (it's both — e.g. an architectural decision with a contract): write the
contract in the official doc **and** a `knowledge/` page with the "why", linking
one to the other.

## 5th destination — persona/preference (`.claude/rules/USER.md`)

A different axis from the 4 types: those are about **the project**; this is about
**how to work with the user**. Heuristic:

> **Is this a preference / pet-peeve / personal convention about HOW to work with
> me (not a project fact)?** → `.claude/rules/USER.md`.

The path is configurable (`[memory] persona_file` in `brain.config.toml`). On
Claude Code, `.claude/rules/*.md` is **committed** (survives the ephemeral/web
container) and **auto-loaded every session**; pull-based agents (Codex/Gemini)
point the file from `AGENTS.md` instead. Same human write-gate as the other
destinations; keep the file compact. **Don't confuse:** a fact that touches
code/tests is a contract (gated), not persona.

## Trigger 1 — explicit verb

Fires the capture flow when the human says, in chat:
- `/capture <what>` (slash command), or
- natural phrases: **"capture this"**, **"save to the brain"**, "remember this decision".

## Trigger 2 — proactive agent (level: balanced)

The agent **offers** to record (does not write) when it detects, in the
conversation:
- a **durable decision** ("let's do it this way", "we decided not to");
- a reusable **lesson/gotcha** ("the problem was X");
- an external **source** brought up and discussed (link/article) → offers to ingest as a `source`;
- a good **synthesis/answer** worth keeping as a future reference → offers to record as `knowledge` (*query-filed-back*: the good answer becomes a page);
- a durable **preference/persona** ("I prefer", "from now on", "it bugs me when", "don't make me repeat") → offers to record in `.claude/rules/USER.md`.

(Levels: `conservative` = decisions/contracts only; `balanced` = + lessons and
sources; `aggressive` = + any new concept/definition. This vault: **balanced**.)

### Anti-nag guardrails

- Only offer if: (a) it's durable — it would matter in a future session, (b) it
  isn't already captured, (c) it has a clear home in one of the types.
- Ask **once, at a natural boundary** (end of a thought/task), **never every
  message**; **batch** several items into one question.
- Lean offer: *"this looks like a [concept/source/contract] — record it in
  [destination]?"*. Declining is cheap; **don't re-ask the same item** in the session.
- In a focused code task or `/low-token`, stay **quiet** — except for a
  **contract** (worth flagging, since it touches the gated layer).

## Capture flow (what the agent does)

1. **Classify** the content into one of the 4 types (apply the boundary heuristic).
2. If an **external source** is involved → first create
   `raw/sources/<YYYY-MM-DD>-<slug>.md` (immutable) from `templates/template-source.md`.
3. **Write to the destination**: `knowledge/<area>/<slug>.md` from
   `templates/template-knowledge.md`, or the official doc/skill if it's a contract.
4. **Cite the source**: a `sources:` field pointing to `raw/` or a URL — every
   claim traces to an origin (anti-model-collapse).
5. **Update the index**: add a one-line entry in `knowledge/index.md` under the area.
6. **Report in one line** what was written and where. No file-by-file permission.

> **No secrets (ingest filter):** never capture tokens, connection strings,
> credentials, or personal data (PII). Pasted chat content (logs, configs,
> transcripts) is redacted/omitted before writing — applies to `raw/sources/`
> and `knowledge/` alike. The automated sweep redaction is **best-effort**
> (pattern-based), not a guarantee — review sweep/capture files before committing,
> since the vault is git-versioned.

## Verification, search, and staleness

Captured knowledge is maintained on three rails (the "Lint/Query" operations of
the LLM-wiki pattern):

- **Structural lint (automatic):** the `vault_sync` validator (in preflight/CI)
  flags broken provenance (`sources:` that doesn't exist → FAIL), a stale
  `knowledge/` page (older than the configured `stale_days` → WARN), and an
  orphan source in `raw/sources/` (WARN).
- **Search (Query):** `python -m hipocampo.search "<terms>"` ranks `knowledge/`,
  `insights/`, `specs/`, and `raw/sources/`. Fast path: a SQLite FTS5 index
  (incremental, with RRF graph fusion), automatic fallback to pure-Python BM25.

**Staleness marker:** perishable claims carry a `[as of YYYY-MM]` suffix in the
body (e.g. "we use managed Postgres *[as of 2026-05]*") so a future review knows
what to re-check.

## Immutability of `raw/`

`raw/sources/` is **append-only**: the agent reads, cites, and never rewrites it.
It is the verification baseline against model collapse. Corrections in
understanding go to the `knowledge/` page, not to the source.
