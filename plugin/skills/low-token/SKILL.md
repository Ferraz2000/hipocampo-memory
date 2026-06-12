---
name: low-token
description: Lean execution mode for small, well-scoped tasks — minimum reading, no vault, no discovery, smallest correct change. Use when the user says "/low-token <task>", "lean mode", "minimal context".
---

# low-token — lean execution mode

For small, well-delimited tasks where loading context would cost more than the
task itself.

## Mode (applies to this task only)

Read **only**:
1. `AGENTS.md` (root router) + the relevant subtree file, if any.
2. The code files directly affected by the change.
3. The area skill **if already named in the routing** for this kind of task.

Do **not**: read the vault (no knowledge/insights/specs), run discovery, or offer
proactive captures — with **one exception**: if the change touches a
`[[doc_sync]]` area, say so and ship the doc in the same commit (the gate blocks
otherwise; staying silent just delays the failure to commit time).

## Execution

1. Implement the smallest correct change.
2. Run only the tests covering the touched files.
3. Report in a few lines: change, files, test result.

## Rules

- If mid-task the scope turns out NOT to be small (cross-layer, contract change,
  unclear requirements), stop and say so — don't stretch lean mode over work that
  needs real context.
- Capture-sweep still runs at session end (it's a hook); that's fine — it
  proposes, it doesn't read.
