---
name: recall
description: Search durable memory (the vault) mid-task and pull only the relevant notes into context, instead of asking the user about past decisions. Use proactively before asking "what did we decide about X", when you need prior rationale, conventions, or history; or when the user says "/recall", "recall", "what do we know about", "check the brain/memory".
---

# recall — pull relevant memory into context on demand

The agent-callable read side of the kit — the `LoadMemoryTool` half (the
SessionStart briefing is the `PreloadMemoryTool` half). **Before asking the user
about a past decision, convention, or rationale, recall first.**

## Task

1. **Compose a focused query** from the current need — concept words, not the
   user's literal phrasing. The index fuses BM25 with the optional `[semantic]`
   vector ranking, so paraphrase and synonyms are fine ("session expiry" finds a
   note written as "token TTL / auto-logout").
2. **Search** (returns ranked **pointers**, not whole notes):
   `python3 -m hipocampo.search "<query>"` — pure BM25, always available; or
   `python3 -m hipocampo.index "<query>"` — FTS5 + graph/semantic RRF when present.
3. **Index-first read** (context-rot defense): open only the top 1–3 pointers that
   look relevant; never bulk-read the vault. Orient from `knowledge/index.md` first
   when you need the lay of the land.
4. **Use it and cite the path.** If nothing relevant returns, say so in one line,
   then ask the user.

## Rules

- Read-only — recall writes nothing. To save something, that's `/capture`.
- Prefer the smallest set of notes that answers the need (token budget).
- The `[semantic]` vector ranking is opt-in (`[semantic] enabled` + the extra
  installed + an extension-loadable sqlite); without it, recall runs on pure BM25.
