---
title: Semi-automatic capture drafts candidates; the human still gates writes
type: knowledge
area: architecture
status: active
confidence: high
provenance: extracted
sources:
  - raw/sources/2026-06-17-agent-memory-landscape.md
created: 2026-06-17
updated: 2026-06-17
valid_until: ""
superseded_by: ""
tags: [knowledge, architecture, capture, human-gate]
---

# Semi-automatic capture drafts candidates; the human still gates writes

> The session-end sweep can run in **`draft` mode**: it stages capture candidates
> in the disposable `.brain-cache/`, never the vault. The human approves via
> `/capture --review`, where the agent reasons over the real transcript and drafts
> proper notes. This keeps the human write-gate while fixing the sparse-vault hole.

## Context

A purely manual `/capture` leaves the vault empty — nobody remembers to file — and
an empty vault makes the semantic tier worthless. The opposite extreme (capture
everything automatically, like server-side LLM consolidation) trades away the
human gate and floods memory with noise. Proactive memory extraction + sleep-time
consolidation (see `raw/sources/2026-06-17-agent-memory-landscape.md`) point to a
middle path.

## The decision / concept

- `[capture.auto] mode` = `inbox` (legacy) | `draft` | `off`. In `draft`, the
  `capture_sweep` hook stages checkbox candidates + a `transcript:` pointer in the
  disposable cache, deduped per session; the SessionStart briefing surfaces them.
- The regex hits are **signals, not final wording**: `/capture --review` reads the
  real session and drafts well-formed, deduped notes for one-pass human approval.
- **Why:** the agent does the drafting, the human keeps the gate — recall density
  without losing curation, and no LLM calls from the scripts (the reasoning lives
  in the review skill, not in Python). Pairs with the semantic tier: draft fills
  the vault, semantic makes it findable.

## Related

- [[semantic-search-tier]]
