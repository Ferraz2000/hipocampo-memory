#!/usr/bin/env python3
"""Forcing function: a change to a sensitive code area must ship with a doc
update in the same commit/PR (or a Doc Impact Report).

Rules come entirely from ``brain.config.toml`` (``[[doc_sync]]`` tables): each
rule has ``paths`` (globs) and ``docs`` (exact paths). A staged file matching a
rule's ``paths`` requires at least one of that rule's ``docs`` in the same diff.
A file matching any ``doc_sync_escape_globs`` (e.g. a Doc Impact Report)
satisfies every rule for that commit.

Modes:
  --staged    Validate only the staged diff (HEAD vs index). Used by the
              pre-commit hook — blocks the commit per isolated area.
  default     Branch diff. Base ref resolved from --base, CI env, or the
              configured base branch.

Never hard-fails when it cannot determine changes (exit 0); fails only on a real
sensitive-area-without-doc violation.
"""

import sys

from .. import config as _config
from ..globs import match_any
from . import _git


def failures(changed, cfg):
    """Failure messages for the changed-file list (empty list = pass)."""
    # A Doc Impact Report (or any configured escape) excuses every rule.
    if any(match_any(f, cfg.doc_sync_escape_globs) for f in changed):
        return []

    out = []
    for rule in cfg.doc_sync:
        name = rule.get("name", "(unnamed rule)")
        paths = rule.get("paths", [])
        docs = rule.get("docs", [])
        touched = [f for f in changed if match_any(f, paths)]
        if not touched:
            continue
        # docs may be exact paths or globs; a changed file matching any satisfies it.
        if any(match_any(c, docs) for c in changed):
            continue
        out.append(
            f"Sensitive area changed without its doc update: {name}\n"
            f"  Files:  {', '.join(touched)}\n"
            f"  Update one of: {', '.join(docs) or '(no docs configured for this rule)'}\n"
            f"  Or add a Doc Impact Report matching: {', '.join(cfg.doc_sync_escape_globs)}"
        )
    return out


def _report(changed, cfg, label):
    print(f"feature-doc-sync: {len(changed)} file(s) {label}.")
    fails = failures(changed, cfg)
    if fails:
        print("\nfeature-doc-sync validation FAILED")
        print("=" * 72)
        print("\n\n".join(fails))
        print("=" * 72)
        return 1
    print("feature-doc-sync: validation passed.")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        cfg = _config.load_config()
    except _config.ConfigError as e:
        print(f"feature-doc-sync: {e}")
        return 1

    if not cfg.doc_sync:
        print("feature-doc-sync: no [[doc_sync]] rules configured; nothing to check.")
        return 0

    if "--staged" in argv:
        print("feature-doc-sync: staged mode (git diff --cached)")
        changed = _git.staged_files(cfg)
        if changed is None:
            print("feature-doc-sync: git diff --cached failed; skipping.")
            return 0
        if not changed:
            print("feature-doc-sync: nothing staged; nothing to validate.")
            return 0
        return _report(changed, cfg, "staged")

    override = argv[argv.index("--base") + 1] if "--base" in argv else None
    diff_range, source = _git.resolve_range(cfg, override)
    if diff_range is None:
        print("feature-doc-sync: no base ref available; skipping.")
        return 0
    print(f"feature-doc-sync: diff range = {diff_range} ({source})")
    changed = _git.changed_files(cfg, diff_range)
    if changed is None:
        print("feature-doc-sync: git diff failed; skipping.")
        return 0
    if not changed:
        print("feature-doc-sync: no files changed; nothing to validate.")
        return 0
    return _report(changed, cfg, "changed")


if __name__ == "__main__":
    sys.exit(main())
