---
name: brain-router-init
description: Generate a lean, operational AGENTS.md router for this repo (any language) plus the CLAUDE.md pointer and a .claude/rules/USER.md persona seed. Use after brain-init, or when the user says "generate the router", "set up AGENTS.md", "brain-router-init".
---

# brain-router-init — generate the agent router

Produce a **short, operational** `AGENTS.md` — vague, long instruction files
measurably tax reasoning, so keep it concrete (commands, paths) and brief.

## Steps

1. **Detect the stack.** Inspect manifests to identify language/build/test:
   `package.json`, `pyproject.toml`/`requirements.txt`, `go.mod`, `Cargo.toml`,
   `*.csproj`/`*.sln`, `pom.xml`/`build.gradle`, `Gemfile`, etc. Note the test and
   build commands.
2. **Map subsystems.** Skim top-level source dirs to list the few real areas of the
   repo (don't over-enumerate).
3. **Write `AGENTS.md`** at the repo root with these sections, lean:
   - **Read order**: the touched subsystem's doc → nearest subtree `AGENTS.md` →
     area skill → `<vault>/knowledge/index.md` (index-first) for non-trivial work.
   - **Build/test**: the exact commands detected.
   - **Memory**: point to `<vault>/capture.md` (write-gated capture) and
     `<vault>/context-budget.md` (never bulk-read the vault).
   - **Doc-sync**: note that `[[doc_sync]]` rules in `brain.config.toml` gate
     sensitive areas (the pre-commit hook blocks a change lacking its doc).
   - **Global rules**: only concrete, enforceable ones. Include the recitation
     rule for long tasks: re-state the working todo at each phase boundary to fight
     lost-in-the-middle (Manus).
4. **Write `CLAUDE.md`** containing just `@AGENTS.md` (the official Claude Code
   bridge), unless one already exists — then append the import if missing.
5. **Seed `.claude/rules/USER.md`** (persona/preferences, the 4th memory layer) if
   absent — a short template with empty Communication / Pet-peeves / Conventions
   sections. Committed + auto-loaded every session.
6. **Path-scoped rules (optional):** for rules that only apply to one area, write
   them as `.claude/rules/<name>.md` with a `paths:` glob frontmatter instead of
   bloating `AGENTS.md` — they load only when the agent touches matching files
   (index-first by path, native to Claude Code).
7. **Cross-agent (optional):** offer to mirror skills into `.agents/skills` (Codex)
   and set Gemini's `contextFileName` to `AGENTS.md`.

## Rules

- Keep `AGENTS.md` under ~120 lines. Every directive carries a command or a path.
- Don't invent rules the repo doesn't have. Detect, don't assume.
- Never overwrite an existing `AGENTS.md`/`CLAUDE.md` without showing a diff first.
