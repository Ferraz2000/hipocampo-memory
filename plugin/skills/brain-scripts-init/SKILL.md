---
name: brain-scripts-init
description: Vendor the hipocampo validation scripts, git hooks, and CI workflow into the current repo so the doc-sync gate and preflight run locally and in CI. Use after brain-init, or when the user says "vendor the scripts", "set up the hooks/CI", "brain-scripts-init".
---

# brain-scripts-init — vendor scripts, hooks, CI

Make the kit's machinery run in this repo, independent of how the plugin was
installed (hooks/CI need the package importable at the repo root).

## Steps

0. **One `AskUserQuestion` round** (3 questions, then act — no more asking):
   - **Which agents are in use?** (multiSelect: Claude Code / Codex / Gemini) —
     Codex → mirror skills into `.agents/skills/`; Gemini → set
     `contextFileName: AGENTS.md`.
   - **Install the CI workflow?** (not every repo uses GitHub Actions — skip
     step 3 if no)
   - **Native auto-memory policy**: disable (`autoMemoryEnabled: false`) /
     redirect (`autoMemoryDirectory` → the vault inbox, promoted via the
     write-gate) / leave as is.
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
5. **Apply the auto-memory answer** from step 0 in `.claude/settings.json`
   (never change settings silently beyond what was chosen).
6. **Report** what was vendored + how to add the first doc-sync rule (point to the
   `[[doc_sync]]` block in `brain.config.toml`).

## Rules

- Idempotent. Don't clobber a user-modified vendored file — if a file differs from
  the kit's version and lacks the managed header, stop and ask.
- The package is vendored (not pip-installed) so hooks and CI work with zero setup
  in the target repo.
- `git commit --no-verify` to bypass the doc-sync gate is off-limits without
  explicit owner authorization per commit.
