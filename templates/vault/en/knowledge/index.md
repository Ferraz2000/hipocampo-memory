---
title: Knowledge — navigation index
type: index
area: meta
status: active
created: {{DATE}}
updated: {{DATE}}
tags: [knowledge, index, navigation]
---

# Knowledge — navigation index

> **Read-cheap entry point** (Karpathy LLM-wiki). Lists every
> `knowledge/<area>/X.md` with a one-line hook + its sources. Agents read THIS
> (~a few KB) → identify the relevant pages → load only those. Never bulk-read
> the vault.
>
> When to read: the task touches one of the areas below and is non-trivial
> (architectural decision, flow-gate change, cross-layer change). Routine code
> tasks follow the skill/official doc — the index is an entry point, not a
> universal obligation.
>
> How it's kept: updated by `/registra` when a page is created/moved. The
> `vault_sync` validator enforces consistency (page without entry → FAIL; entry
> without file → FAIL).

<!--
Areas and entries appear here as knowledge is captured. One line per page:

## meta
- [some-decision](meta/some-decision.md) — one-line hook. Sources: raw/sources/<file>.md.

## architecture
- [some-pattern](architecture/some-pattern.md) — one-line hook. Sources: ...
-->
