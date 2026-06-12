---
name: brain-scripts-init
description: Vendor the hipocampo validation scripts, git hooks, and CI workflow into the current repo so the doc-sync gate and preflight run locally and in CI. Use after brain-init, or when the user says "vendor the scripts", "set up the hooks/CI", "brain-scripts-init".
---

# brain-scripts-init — vendor scripts, hooks, CI

Make the kit's machinery run in this repo, independent of how the plugin was
installed (hooks/CI need the package importable at the repo root).

## Steps

1. **Vendor the package.** Copy `${CLAUDE_PLUGIN_ROOT}/hipocampo/` to the repo root
   as `hipocampo/` (exclude `tests/`). Each vendored file keeps a header line:
   `# hipocampo vX.Y.Z — managed; edit via brain.config.toml`. Record the version
   and source commit in `hipocampo/.hipocampo-manifest.json` for `brain-update`.
2. **Install the git hooks.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/githooks/`
   (`pre-commit`, `pre-push`) into `.githooks/`, make them executable, and set
   `git config core.hooksPath .githooks`.
3. **Install CI.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/ci/agent-docs.yml` to
   `.github/workflows/agent-docs.yml`.
4. **Sanity check.** Run `python3 -m hipocampo.preflight` and report the result. A
   repo with no `[[doc_sync]]` rules yet passes cleanly.
5. **Native auto-memory policy.** Claude Code's auto-memory writes outside git
   without a write-gate, competing with the vault. Offer to either disable it
   (`autoMemoryEnabled: false` in `.claude/settings.json`) or point
   `autoMemoryDirectory` at the vault inbox so the capture-sweep promotes it
   through the write-gate. Let the user choose; don't change settings silently.
6. **Report** what was vendored + how to add the first doc-sync rule (point to the
   `[[doc_sync]]` block in `brain.config.toml`).

## Rules

- Idempotent. Don't clobber a user-modified vendored file — if a file differs from
  the kit's version and lacks the managed header, stop and ask.
- The package is vendored (not pip-installed) so hooks and CI work with zero setup
  in the target repo.
- `git commit --no-verify` to bypass the doc-sync gate is off-limits without
  explicit owner authorization per commit.
