---
name: brain-scripts-init
description: Vendor the hipocampo validation scripts, git hooks, and CI workflow into the current repo so the doc-sync gate and preflight run locally and in CI. Use after brain-init, or when the user says "vendor the scripts", "set up the hooks/CI", "brain-scripts-init".
---

# brain-scripts-init — vendor scripts, hooks, CI

Make the kit's machinery run in this repo, independent of how the plugin was
installed (hooks/CI need the package importable at the repo root).

## Steps

0. **Interview** (in Claude Code use ONE `AskUserQuestion` round; in Codex/Gemini
   just ask in plain text — those agents lack `AskUserQuestion`). 4 questions,
   then act — no more asking:
   - **Which agents are in use?** (multi-select: Claude Code / Codex / Gemini) —
     drives which session-hook wiring (step 5) and router settings (handled by
     `brain-router-init`) get installed. Skills themselves are read natively by
     all three (`npx skills add`, or copy `plugin/skills/**` into `.agents/skills/`
     for Codex / `.gemini/skills/` for Gemini) — no wrappers.
   - **Enforcement level** — how hard the doc-sync gate pushes back, written as
     `[enforcement]` in `brain.config.toml`. Offer three presets and **recommend
     "advisory-local"** (you're never stuck mid-task, but drift still can't merge):
     - **Strict** → `pre_commit/pre_push/ci = "block"` (blocks commit + push + CI).
     - **Advisory-local (recommended)** → `pre_commit/pre_push = "warn"`,
       `ci = "block"` (local just surfaces findings; CI is the backstop).
     - **Off-local** → `pre_commit/pre_push = "off"`, `ci = "block"`.
     Explain block = fail, warn = print but don't block, off = skip; and that CI
     stays strict so the gate still bites at merge time.
   - **Install the CI workflow?** (not every repo uses GitHub Actions — skip
     step 3 if no; if no, the `ci` enforcement value is moot until added)
   - **Native auto-memory policy**: disable / redirect to the vault inbox
     (promoted via the write-gate) / leave as is. Applies where the agent has the
     feature (Claude Code `.claude/settings.json` `autoMemoryEnabled`/
     `autoMemoryDirectory`; Gemini Auto Memory is preview; Codex has none).
1. **Vendor the package.** Copy `${CLAUDE_PLUGIN_ROOT}/hipocampo/` to the repo root
   as `hipocampo/` (exclude `tests/`). Get the version from
   `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` (`version` field) and the
   source commit from `git -C ${CLAUDE_PLUGIN_ROOT} rev-parse --short HEAD`. Write
   `hipocampo/.hipocampo-manifest.json`:
   ```json
   {"version": "<version>", "source_commit": "<short-sha>", "vendored_at": "<YYYY-MM-DD>"}
   ```
   (the manifest is what `brain-update` reads to diff against the kit). Adding a
   per-file managed header is optional and not required for `brain-update`.
   **Also create or append the repo-root `.gitignore`** from
   `${CLAUDE_PLUGIN_ROOT}/templates/gitignore` so the derived cache
   (`.brain-cache/`) and `__pycache__/`/`*.pyc` are never committed — the cache is
   disposable and would otherwise churn on every search.
2. **Install the git hooks.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/githooks/`
   (`pre-commit`, `pre-push`) into `.githooks/`, make them executable, and set
   `git config core.hooksPath .githooks`.
3. **Install CI.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/ci/agent-docs.yml` to
   `.github/workflows/agent-docs.yml`, and edit its `branches: [main]` to match
   the repo's actual base branch (`base_branch` in `brain.config.toml`) —
   otherwise push-mode CI never triggers.
4. **Sanity check.** Run `python3 -m hipocampo.preflight` and report the result. A
   repo with no `[[doc_sync]]` rules yet passes cleanly.
5. **Wire the session hooks per agent** (briefing at session start + capture-sweep
   at session end — the same agent-agnostic `hipocampo.hooks.*` modules, only the
   wiring differs). Install from `${CLAUDE_PLUGIN_ROOT}/templates/hooks/` for each
   selected agent:
   - **Claude Code** → already carried by the plugin (`plugin/hooks/hooks.json`);
     nothing to vendor.
   - **Codex** → copy `templates/hooks/codex/hooks.json` to `.codex/hooks.json`
     (or `~/.codex/hooks.json` for reliability), and tell the user to run `/hooks`
     once to trust it. Note: Codex hooks are experimental.
   - **Gemini** → merge the `hooks` object from
     `templates/hooks/gemini/settings.hooks.json` into `.gemini/settings.json`
     (don't clobber existing keys).
   - Write the chosen **`[enforcement]`** preset (from step 0) into
     `brain.config.toml` (omit the block to keep the all-`block` default).
   - Apply the **auto-memory** answer from step 0 in the agent's own settings
     (Claude `.claude/settings.json`; Gemini if available; Codex skip with a note).
6. **Report** what was vendored + wired (per agent) + the chosen enforcement level
   + how to add the first doc-sync rule (point to the `[[doc_sync]]` block in
   `brain.config.toml`).

## Rules

- Idempotent. Don't clobber a user-modified vendored file — if a file differs from
  the kit's version and lacks the managed header, stop and ask.
- The package is vendored (not pip-installed) so hooks and CI work with zero setup
  in the target repo.
- `git commit --no-verify` to bypass the doc-sync gate is off-limits without
  explicit owner authorization per commit.
