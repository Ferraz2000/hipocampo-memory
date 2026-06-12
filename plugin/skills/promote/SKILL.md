---
name: promote
description: Promote an insight into a durable artifact — a spec, an ADR, or a tracker issue — and mark the insight promoted. Use when the user says "/promote <insight> <spec|adr|issue>", "turn this insight into a spec/ADR/issue".
---

# promote — insight → spec | adr | issue

A proposal that won becomes a contract-shaped artifact; the insight's frontmatter
records the promotion (single source of truth).

## Task

`$ARGUMENTS` = `<insight path-or-slug> <type>`, type ∈ {spec, adr, issue}.

1. **Read the insight** (problem, recommendation, scores, history).
2. **Create the artifact**:
   - **spec** → `<vault>/specs/<YYYY-MM-DD>-<slug>.md` (`type: spec`,
     `status: draft`): Problem, Approach, Touched areas, Risks, Acceptance
     criteria, Out of scope. Same shape as the `spec` skill.
   - **adr** → `<vault>/adrs/<NNNN>-<slug>.md` (`type: adr`, `status: proposed`):
     Context, Decision, Consequences, Alternatives considered. Number = next free.
   - **issue** → tracker issue (e.g. `gh issue create`) titled from the insight,
     body = problem + recommendation + link back to the vault path. Confirm with
     the user before creating anything external (it's outward-facing).
3. **Close the loop on the insight**: `status: promoted`, `updated: <date>`, and
   a `## History` bullet linking the artifact (path or issue URL). The artifact
   links back to the insight.
4. **Append one line to `<vault>/log.md>`** and report both paths/URLs.

## Rules

- One insight, one promotion per run.
- Never delete the insight — `promoted` keeps the trail for `challenge`.
- External artifacts (issues) need explicit user confirmation first.
