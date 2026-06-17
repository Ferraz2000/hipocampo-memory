#!/usr/bin/env python3
"""Enforcement layer for the git hooks and CI.

The hooks/CI call THIS, not the validators directly, so the block/warn/off
policy lives in one place: ``[enforcement]`` in ``brain.config.toml``. Validators
themselves always report truthfully (exit non-zero on a real violation); the gate
decides whether that should block.

Per gate point (``brain.config.toml``):
- ``block`` — propagate the underlying exit code (a violation blocks the op).
- ``warn``  — run and surface findings, but always exit 0 (never blocks).
- ``off``   — skip the check entirely (exit 0).

Subcommands map points to checks:
  pre-commit  -> feature_doc_sync --staged   ([enforcement] pre_commit)
  pre-push    -> preflight (all validators)   ([enforcement] pre_push)
  ci          -> preflight (all validators)   ([enforcement] ci)

Usage:
  python -m hipocampo.gate pre-commit
  python -m hipocampo.gate pre-push
  python -m hipocampo.gate ci
"""

import sys

from . import config as _config
from . import preflight as _preflight
from .validators import feature_doc_sync as _feature_doc_sync

# point -> (config key, default check). The check is a zero-arg callable
# returning an exit code; injectable in tests.
_POINTS = {
    "pre-commit": ("pre_commit", lambda: _feature_doc_sync.main(["--staged"])),
    "pre-push": ("pre_push", lambda: _preflight.main([])),
    "ci": ("ci", lambda: _preflight.main([])),
}


def run(point, cfg, runner=None):
    """Apply the configured enforcement mode for ``point``. Returns an exit code."""
    key, default_runner = _POINTS[point]
    runner = runner or default_runner
    mode = cfg.enforcement_mode(key)

    if mode == "off":
        print(f"hipocampo gate [{point}]: enforcement=off — skipped "
              f"(set [enforcement] {key} in brain.config.toml to enable).")
        return 0

    rc = runner()
    if mode == "warn":
        if rc != 0:
            print(f"\nhipocampo gate [{point}]: enforcement=warn — the issues above "
                  f"are ADVISORY, not blocking.\nSet [enforcement] {key} = \"block\" "
                  f"in brain.config.toml to enforce.")
        return 0  # warn never blocks
    return rc  # block: the underlying result decides


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in _POINTS:
        print(f"usage: python -m hipocampo.gate {{{'|'.join(_POINTS)}}}", file=sys.stderr)
        return 2
    try:
        cfg = _config.load_config()
    except _config.ConfigError as e:
        print(f"gate: {e}")
        return 1
    return run(argv[0], cfg)


if __name__ == "__main__":
    sys.exit(main())
