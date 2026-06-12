---
name: archive-closed
description: Compact long-closed insights into a one-line archive index so they stop costing discovery context while staying traceable. Use when the user says "/archive-closed", "compact the insights", "clean up old insights".
---

# archive-closed — compact terminal insights

Insights with a terminal status (closed/implemented/rejected/superseded) are dead
history: kept for traceability, but they shouldn't cost full-page context on every
discovery sweep. This compacts them into an archive index (beads-style semantic
compaction).

## Task

1. **Find terminal insights**: scan `<vault>/insights/**` for `status` in
   {closed, implemented, rejected, superseded}. (Search with `--all` includes them.)
2. **Confirm scope** with the user (e.g. only those older than N months).
3. For each, **append a one-line entry** to `<vault>/insights/_archive-index.md`:
   `- [<title>](<path>) — <status> (<date>) — one-line outcome`.
4. **Optionally collapse the body**: replace the page body (not frontmatter) with a
   pointer to the archive index, keeping the frontmatter intact for traceability.
   Only if the user wants the disk footprint reduced — default is index-only.
5. **Report** how many were archived and the index path.

## Rules

- Frontmatter is truth — never change `status`/dates while archiving; you're only
  summarizing. `raw/` and `knowledge/` are out of scope (this is insights-only).
- Reversible: the full history stays in git; the archive index is additive.
