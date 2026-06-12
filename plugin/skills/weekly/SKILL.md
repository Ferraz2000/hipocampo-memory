---
name: weekly
description: Weekly review cycle over the vault — triage new insights and inbox sweeps, surface stale/expired pages, and propose promotions or closures. Use when the user says "/weekly", "weekly review", "triage the vault".
---

# weekly — review & triage cycle

The maintenance heartbeat: nothing decays silently, nothing good stays buried.
Read bounded; propose; the human decides (write-gate).

## Task

1. **Structural state first** (cheap, scripted):
   - `python3 -m hipocampo.validators.vault_sync` — broken provenance, stale
     pages, expired `valid_until`, orphans, index drift.
   - `python3 -m hipocampo.inbox_decay` (dry-run) — sweeps about to expire.
2. **Inbox triage**: for each pending `_inbox/` sweep, propose a destination
   (knowledge / source / persona / delete) per the capture protocol. Batch into
   ONE question; apply only what's approved.
3. **Insight queue**: list `status: triage` insights with scores; propose for
   each: promote (→ `promote`), activate, or reject (with one-line why).
4. **Stale knowledge**: pages flagged stale/expired → propose refresh, supersede,
   or confirm-still-true (bump `updated`).
5. **Apply approved changes** (frontmatter edits + index/log updates), then run
   vault_sync again — must be green. Append a `## [date] weekly | ...` line to
   `<vault>/log.md`.
6. **Report**: counts (triaged/promoted/rejected/refreshed) + what's queued next
   (`from-roadmap` view).

## Rules

- Propose-then-apply; never bulk-edit without the user's picks.
- Frontmatter-as-truth: status changes happen ONLY in the page's frontmatter.
- Keep it bounded: frontmatter scans, not full-body reads, until an item is picked.
