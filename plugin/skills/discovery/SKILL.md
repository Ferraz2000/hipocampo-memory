---
name: discovery
description: Discovery mode — authorize broad, bounded reading of the vault for audits, cross-cutting insights, or roadmap review. The declared exception to never-bulk-read. Use when the user says "/discovery", "explore the vault", "do discovery on area X", "audit Y".
---

# discovery — broad vault read (the declared exception)

Normally agents do not bulk-read the vault (`context-budget.md`). Discovery mode is
the sanctioned exception — use it **only when the work itself is reading the vault**.

## Task

1. **Declare** at the top of your response that you're in discovery mode and state
   the scope (which area/dirs you'll read).
2. **Read bounded.** Prefer `python3 -m hipocampo.search` to pre-select the relevant
   notes, then read only those. For a wide sweep, delegate to a read-only sub-agent
   that returns a summary (protect the main context).
3. **Produce the artifact** the user asked for — new insight(s) under
   `<vault>/insights/<area>/`, an audit summary, a roadmap review — using the note
   templates and the closed `status` vocabulary from `brain.config.toml`.
4. **Stay in scope.** Don't read beyond the declared area.

## Notes

- New insights are proposals (`status: triage`), scored impact/effort/risk — not
  truth yet. Promote to a spec/ADR/issue when they become a contract.
- Capturing anything durable still goes through the `capture` write-gate.
