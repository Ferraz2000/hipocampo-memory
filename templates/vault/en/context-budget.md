---
title: Context Budget — how agents consult the vault
type: protocol
area: meta
status: active
tags: [agents, protocol, context-budget]
created: {{DATE}}
updated: {{DATE}}
---

# Context Budget — how agents consult the vault

This protocol defines the **context budget** agents (Claude Code, Codex, Gemini)
must respect when working in this repo. Its purpose: keep the vault useful as a
human/agent second brain **without it becoming an automatic token sink**. It is
the empirical answer to context rot — performance degrades as the window fills,
even on trivial tasks.

> Companion docs: [README](README.md), [capture](capture.md), root `AGENTS.md`.

## Principle

The vault is a **cockpit**. Agents must not read vault files automatically. When
an agent needs context, it prefers the official sources (`docs/...`) and the root
routers.

**Broad reading → read-only sub-agent.** Cross-file sweeps (discovery, audit,
"read N files and summarize") should be delegated to a read-only sub-agent that
returns a summary, protecting the main context (*bounded-context principle*).
Where there is no sub-agent (e.g. Codex), limit to the declared scope and discard
what doesn't make it into the result.

> **Sanctioned exception:** a SessionStart hook may inject a **git-derived**
> briefing (session branch, unmerged branches, recent merges) as bounded
> operational context. The source is the real repo state, so it never goes stale.
> No other automatic vault loading is permitted.

## Index-first reads (Karpathy LLM-wiki)

For non-trivial work that touches an area covered by `knowledge/`, read
`knowledge/index.md` **first** (cheap, a few KB), identify the relevant pages,
and load **only those**. Never bulk-read `knowledge/`, and never silently skip it
when the topic clearly matches. Routine code tasks follow the skill/official doc —
the index is the entry point, not a universal obligation.

## Default reading per task

For a normal feature/bugfix/refactor, the agent reads **only**:

1. `AGENTS.md` — root router and global rules.
2. The official doc for the touched subsystem (`docs/...`).
3. The area skill (`.claude/skills/<skill>/SKILL.md`).
4. The code files directly affected by the change.

Everything outside that list needs an explicit trigger.

> **Exception (non-code tasks):** for conceptual/product/decision work (not a
> code task), `knowledge/` is **sanctioned** reading — it's the conceptual-truth
> layer of the hybrid model (see [capture](capture.md)). On code tasks, keep
> skipping the vault as above.

## When to read the rest of the vault

Insights, roadmap, history, and other notes should be read only when:

1. **The user explicitly cites** the file path in the prompt.
2. **Discovery mode is requested** ("do discovery on area Y", "explore the vault").
3. **A slash command** that activates the vault is invoked (`/spec`, `/implement`,
   `/execute-insight`, `/from-roadmap`).
4. **The task itself is to write to the vault** — update an insight, create a
   note, adjust the roadmap.

In any other case, the agent **omits** reading the vault.

## Low-token mode

For small, well-scoped tasks, use `/low-token <task>` or paste this at the top of
the prompt:

```text
Mode: low-token feature mode.
Read only the minimum necessary.
Do not read the whole vault; no insights/roadmap without an explicit ask.
Implement the smallest correct change.
```

Low-token reduces reading to: `AGENTS.md` + the relevant subtree, the directly
affected code files, and the area skill **if already in routing**. No discovery,
no vault reads.

## Captured writes are the only sanctioned automatic write

The only **automatic** write allowed in the vault is **capture** — the protocol
in [capture](capture.md), triggered by `/registra` or an accepted proactive
offer. It is bounded and always human-gated. Outside capture, agents don't write
to the vault without an explicit trigger.

## Acceptance criteria

- A small task (typo, single-file refactor, tests-only change) does **not**
  trigger automatic vault reads.
- The vault stays human-accessible; no note is deleted.
- Slash commands allow using the vault on demand.
