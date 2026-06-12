---
name: spec
description: Create a short, approved-style spec (mini design doc) in the vault from the template — no code. Use when the user says "/spec", "write a spec for X", "design doc for Y".
---

# spec — create a mini design doc

Write a concise spec under `<vault>/specs/`, without touching code.

## Task

1. **Clarify scope** if ambiguous (one `AskUserQuestion`): the goal, the touched
   areas, and the acceptance criteria.
2. **Write** `<vault>/specs/<YYYY-MM-DD>-<slug>.md` from
   `templates/template-insight.md` adapted to a spec shape, with frontmatter
   `type: spec`, `status: draft`, and sections: Problem, Approach, Touched areas,
   Risks, Acceptance criteria, Out of scope.
3. If it came from an existing insight, set the insight's `status: promoted` and
   link the two.
4. **Report** the path and a one-line summary. Don't implement — that's a separate
   step.

## Notes

- A spec is approved-style intent, not a contract yet. Keep it short and concrete.
- Specs are skipped by the status-vocabulary check (`type: spec` has its own
  lifecycle), so `status: draft` is fine.
