---
name: execute-insight
description: Execute exactly one approved insight from the vault, with separate commits for the code and for closing the insight's frontmatter. Use when the user says "/execute-insight <path-or-slug>", "execute this insight", "implement insight X".
---

# execute-insight — execute one approved insight

Small scope, frontmatter-as-truth closure, two commits (the `implemented_in` field
must point at the implementation commit, so the insight closes in a second one).

## Task

1. **Resolve the insight** from `$ARGUMENTS`: a full path under `<vault>/insights/`
   or an exact slug (find exactly one `<slug>.md`; zero or many → stop and ask).
2. **Read it whole**: problem, recommendation, cited files, impact/effort/risk,
   suggested tests, and `depends_on` (an unmet dependency → stop and say which).
3. **Git state**: unrelated changes → stop and ask. On a clean base branch
   (`base_branch` in `brain.config.toml`), create `<type>/<slug>` — `<type>` from
   intent: refactor / perf / fix / feat / test / docs / chore.
4. **Read only what the recommendation needs.** Think before coding; smallest
   correct change; surface assumptions before touching files.
5. **Run the insight's suggested tests** (or the project's smallest sufficient
   suite). If the change hits a `[[doc_sync]]` area, ship the doc in the same
   commit — the pre-commit gate will block otherwise.
6. **Commit 1 (code)**: `<type>(<area>): <summary>`, body citing `Insight: <slug>`.
7. **Commit 2 (closure, insight file only)**: update frontmatter —
   `status: implemented` (or keep `active` + a note when work remains),
   `implemented_in: <sha-of-commit-1>`, `implemented_at`/`updated: <YYYY-MM-DD>`
   — plus a `## History` bullet. Message: `docs(insights): close <slug>`.
8. **Report**: insight, branch, commits, files, tests, final status.

## Rules

- Never mix code and insight closure in one commit.
- One insight per run. Don't read the whole vault — only the target + needed files.
- Don't mark implemented if suggested tests didn't run or the recommendation is
  incomplete — say what's left instead.
- Ambiguous recommendation → ask, don't invent requirements.
