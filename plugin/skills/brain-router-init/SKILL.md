---
name: brain-router-init
description: Generate a lean, operational AGENTS.md router for this repo (any language) plus the CLAUDE.md pointer and a .claude/rules/USER.md persona seed. Use after brain-init, or when the user says "generate the router", "set up AGENTS.md", "brain-router-init".
---

# brain-router-init — generate the agent router

Produce a **short, operational** `AGENTS.md` — vague, long instruction files
measurably tax reasoning, so keep it concrete (commands, paths) and brief.

## Steps

Read `project_mode` from `brain.config.toml` (set by `brain-init`) and branch:

**Existing project — detect, then CONFIRM (one `AskUserQuestion` round):**

1. **Detect the stack.** Inspect manifests to identify language/build/test:
   `package.json`, `pyproject.toml`/`requirements.txt`, `go.mod`, `Cargo.toml`,
   `*.csproj`/`*.sln`, `pom.xml`/`build.gradle`, `Gemfile`, etc. Note the test and
   build commands and the base branch.
2. **Map subsystems** (skim top-level source dirs) and **propose doc-sync
   candidates**: the dirs whose changes should require a doc in the same commit
   (contracts, persistence/migrations, public API, auth). Then ONE
   `AskUserQuestion` round:
   - confirm the detected stack/build/test/base-branch;
   - **multiSelect**: "which of these areas deserve the doc-sync gate?" — write
     the picked ones as `[[doc_sync]]` rules in `brain.config.toml` (the gate is
     born configured, not empty);
   - confirm the architectural pattern if one is visible (Clean/VSA/hexagonal/
     MVC/none) — it becomes a placement rule in the router.

**Greenfield — ask, then generate (one `AskUserQuestion` round, up to 4):**
main **language/stack** (+ framework) · desired **architecture pattern** ·
**test conventions** (framework, TDD?, coverage target) · **commit/PR style**
(conventional commits? base branch? squash?). Generate the router, the
build/test commands, and starter `[[doc_sync]]` rules from the answers.
3. **Write `AGENTS.md`** at the repo root with these sections, lean (when
   `team = true` in the config, include the PR-workflow rule and suggest
   protecting the vault branch):
   - **Read order**: the touched subsystem's doc → nearest subtree `AGENTS.md` →
     area skill → `<vault>/knowledge/index.md` (index-first) for non-trivial work.
   - **Build/test**: the exact commands detected.
   - **Memory**: point to `<vault>/capture.md` (write-gated capture) and
     `<vault>/context-budget.md` (never bulk-read the vault). **Add the recall
     cue** so memory actually gets used: *"Before asking the user about a past
     decision, convention, or rationale, run the `recall` skill (search the vault)
     first."* This is the `LoadMemoryTool` half — without the cue the agent won't
     fire it.
   - **Doc-sync**: note that `[[doc_sync]]` rules in `brain.config.toml` gate
     sensitive areas (the pre-commit hook blocks a change lacking its doc).
   - **Global rules**: only concrete, enforceable ones. Include the recitation
     rule for long tasks: re-state the working todo at each phase boundary to fight
     lost-in-the-middle (Manus).
4. **Make the router load on every selected agent** (`AGENTS.md` is the single
   source; each agent reaches it differently):
   - **Claude Code** → write `CLAUDE.md` containing just `@AGENTS.md` (the official
     bridge), unless one exists — then append the import if missing.
   - **Codex** → nothing to do; Codex auto-discovers `AGENTS.md`.
   - **Gemini** → set `context.fileName` to `["AGENTS.md", "GEMINI.md"]` in
     `.gemini/settings.json` (older Gemini builds use the flat `contextFileName`
     key — write the nested form, mention the old one). This is the one manual
     router step Gemini needs.
5. **Seed the persona file** (persona/preferences, the 4th memory layer) if absent
   — a short template with empty Communication / Pet-peeves / Conventions sections.
   Path is `[memory] persona_file` in `brain.config.toml` (default
   `.claude/rules/USER.md`). On Claude Code it auto-loads; on Codex/Gemini set it
   to a router-referenced path (e.g. `<vault>/USER.md`) and link it from `AGENTS.md`
   so it's pulled in.
6. **Path-scoped rules (Claude Code only, optional):** for rules that apply to one
   area, write them as `.claude/rules/<name>.md` with a `paths:` glob frontmatter
   instead of bloating `AGENTS.md` — they load only when the agent touches matching
   files (native to Claude Code; Codex/Gemini have no equivalent, so fold such
   rules into `AGENTS.md` there).
7. **Skills are native everywhere:** Codex reads `.agents/skills/`, Gemini reads
   `.gemini/skills/`; `npx skills add` (or `brain-scripts-init`) places them. No
   wrappers needed.

## Rules

- Keep `AGENTS.md` under ~120 lines. Every directive carries a command or a path.
- Don't invent rules the repo doesn't have. Detect, don't assume.
- Never overwrite an existing `AGENTS.md`/`CLAUDE.md` without showing a diff first.
