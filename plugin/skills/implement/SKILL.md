---
name: implement
description: Implement an already-approved spec from the vault (specs/), staying inside its declared scope and acceptance criteria. Use when the user says "/implement <spec>", "implement the spec", "build what the spec says".
---

# implement — build an approved spec

The spec is the contract: scope, acceptance criteria, out-of-scope. You execute
it; you don't re-design it.

## Task

1. **Resolve the spec** from `$ARGUMENTS` (path under `<vault>/specs/` or slug).
   `status` should be approved/ready — `draft` → confirm with the user first.
2. **Read the spec whole**: approach, touched areas, acceptance criteria,
   out-of-scope. Read only the code those areas require.
3. **Branch** off the base branch (`feat/<slug>` or per the spec's type).
4. **Implement to the acceptance criteria** — smallest correct change; anything
   beyond the spec's scope gets noted, not built. If a criterion is untestable or
   contradictory, stop and ask.
5. **Tests**: cover each acceptance criterion; run the touched suites. Doc-sync
   areas ship their doc in the same commit (the gate enforces it).
6. **Close the loop**: set the spec's `status: implemented` (+ `updated`) in a
   separate docs commit; if the spec came from an insight, close that insight too
   (see `execute-insight` rules).
7. **Report**: spec, branch, commits, criteria→evidence mapping, leftovers.

## Rules

- The spec bounds the work. Scope creep → new insight, not silent extra code.
- Acceptance criteria unmet → don't mark implemented; report the gap.
- Don't read the whole vault; the spec + cited files only.
