---
name: postmortem
description: Mine the just-finished branch/PR for durable lessons and propose them as vault captures (insights or knowledge) — the user picks, the agent files. Use when the user says "/postmortem", "capture lessons from this branch", "what did we learn".
---

# postmortem — lessons from the branch

Complements `registra` (captures from conversation) and `discover-standards`
(from code at rest): this captures from **the diff and the journey** — what broke,
what surprised, what should never happen again.

## Task

1. **Scope**: the current branch vs the base branch (`git log` + `git diff --stat
   <base>...HEAD`); plus the conversation's failures/retries if available.
2. **Mine for lessons** worth a future session:
   - gotchas that cost time (wrong assumption, environment trap, flaky test);
   - decisions made mid-flight that aren't documented anywhere;
   - patterns proven good/bad by this work (candidate for `knowledge/` or a
     `[[doc_sync]]` rule).
3. **Propose, don't write**: a numbered list — each item with a one-line lesson +
   suggested destination (`insights/<area>/` proposal, `knowledge/<area>/`
   concept, or persona). The user picks numbers.
4. **File the picks** per the capture protocol (templates, sources = the
   branch/PR/commits, index entry, log line). Write-gate respected.
5. **Report** what was filed where, one line each.

## Rules

- Only durable items — "would this matter in a month?" filters the list.
- Cite commits/files as `sources:` (provenance even for internal lessons).
- No secrets; redact pasted output before filing.
