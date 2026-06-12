---
title: Vault — overview & conventions
type: index
area: meta
status: active
tags: [vault, second-brain, conventions]
created: {{DATE}}
updated: {{DATE}}
---

# Vault — overview & conventions

This is the project's second brain: durable, git-versioned, human-gated memory
for coding agents. Scaffolded by [hipocampo](https://github.com/Ferraz2000/HipoCampo).

> **Agents:** do not bulk-read this vault. Follow [context-budget](context-budget.md)
> (index-first reads, never bulk-read) and [capture](capture.md) (how chat becomes
> a durable note, with a human write-gate).

## Layout

| Path | What | Truth? |
|------|------|--------|
| `knowledge/` | durable concepts & decisions (the wiki) | yes |
| `knowledge/index.md` | cheap index-first entry point | — |
| `knowledge/_inbox/` | auto-capture sweeps awaiting triage | no (ephemeral) |
| `insights/` | scored proposals ("should we?") | not yet |
| `raw/sources/` | immutable ingested sources (provenance) | anchor |
| `specs/` | approved mini design docs | yes |
| `adrs/` | architectural decision records | yes |
| `log.md` | append-only chronological log of ingests/decisions | — |
| `templates/` | note templates | — |

## Canonical frontmatter

Frontmatter is **machine truth**. Any dashboard/readout is a projection of it,
never hand-curated.

**knowledge page:**
```yaml
---
title: ...
type: knowledge
area: <one of the configured areas>
status: active        # active | superseded
confidence: high      # low | medium | high
provenance: inferred  # extracted | inferred | ambiguous
sources:              # every claim traces to an origin
  - raw/sources/<file>.md   # or an https URL
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
---
```

**insight (proposal):** adds `impact`/`effort`/`risk`/`confidence`
(low/medium/high) and `next_step`; `status` from the closed set below.

**source:** `type: source`, `source_type`, `url`, `provenance: external`,
`retrieved`.

## Closed status vocabulary (insights)

`triage` · `active` · `deferred` · `implemented` · `closed` · `rejected` ·
`superseded` · `promoted`

To close/reopen/re-prioritize, edit **only** the insight's frontmatter. The
`vault_sync` validator enforces the closed vocabulary and the index consistency.

## Global rules

- **No secrets in the vault.** Never commit tokens, connection strings,
  credentials, or PII. Redact pasted chat content before capturing.
- **`raw/` is append-only.** Read and cite, never rewrite; corrections go to the
  `knowledge/` page.
- **Index-first.** A new/moved `knowledge/` page gets a one-line entry in
  `knowledge/index.md` in the same change.
