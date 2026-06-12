---
name: garden
description: Run a gardener pass over the vault — find contradictions, stale claims, orphan sources, and missing cross-links, then propose fixes. Use when the user says "/garden", "tidy the vault", "lint the knowledge base", or periodically.
---

# garden — lint & consolidate the vault

The agent-driven counterpart to the structural `vault_sync` validator: it catches
the things a regex can't (contradictions, drift, missing links). Implements the
LLM-wiki "lint pass" + A-MEM "memory evolution" (ingest updates old pages).

## Task

1. **Run the structural lint first**: `python3 -m hipocampo.validators.vault_sync`
   and `python3 -m hipocampo.inbox_decay` (dry-run) to surface broken provenance,
   stale pages, orphans, and stale sweeps.
2. **Read bounded** (use `hipocampo.search` to pre-select; delegate wide sweeps to a
   read-only sub-agent). Look for:
   - **Contradictions** — two `knowledge/` pages asserting incompatible things.
   - **Stale claims** — `[as of YYYY-MM]` markers or `valid_until` past due.
   - **Orphans** — `raw/sources/` not cited; `knowledge/` pages missing from the index.
   - **Missing cross-links** — related pages that don't reference each other (`[[...]]`).
3. **Propose fixes** as a short list (don't apply silently): merge/supersede,
   refresh a dated claim, add an index entry or backlink, retire a dead source.
4. **Apply only what the user approves** (write-gate), then update
   `knowledge/index.md` and append a `log.md` line.

## Rules

- Propose before editing; the human approves. `raw/` stays append-only.
- When a new finding contradicts an old page, prefer **superseding** (set
  `superseded_by`) over deleting — keep the history for `/challenge`.
