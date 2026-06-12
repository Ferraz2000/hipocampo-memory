---
name: brain-update
description: Update the vendored hipocampo scripts/hooks/CI in this repo to the kit's current version without clobbering local changes or any vault content. Use when the user says "update hipocampo", "bump the kit", "brain-update".
---

# brain-update — update vendored files without clobber

Bring the repo's vendored `hipocampo/` package, git hooks, and CI up to the kit's
current version. Never touch the vault (`docs/brain/` etc.) or `brain.config.toml`.

## Steps

1. **Read the manifest** `hipocampo/.hipocampo-manifest.json` for the vendored
   version and source commit. Compare to `${CLAUDE_PLUGIN_ROOT}` (current kit
   version from its `.claude-plugin/plugin.json`).
2. **Three-way diff per file** (BMAD `quick-update` style): base = the version the
   repo vendored, theirs = the kit's current file, ours = the repo's current file.
   - Unchanged locally → overwrite with the kit's version.
   - Locally modified → show the diff and ask before overwriting.
3. **Apply** the accepted updates; refresh the manifest version + commit.
4. **Refuse major upgrades silently.** If the kit's major version jumped, surface
   the changelog/breaking notes and confirm before proceeding.
5. **Verify** with `python3 -m hipocampo.preflight` and report what changed.

## Rules

- Never modify vault content, `brain.config.toml`, or `.claude/rules/USER.md` —
  those are the user's, not the kit's.
- Conventional Commit the update (`chore(hipocampo): bump vendored kit to vX.Y.Z`).
