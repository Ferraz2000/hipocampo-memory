#!/usr/bin/env python3
"""Run every configured validator in sequence (pure Python, no shell needed).

This is the canonical preflight: the same set runs in the pre-push hook and in
CI. If it passes, the push is safe. The validator list comes from
``brain.config.toml`` (``validators = [...]``); each name maps to a module under
``hipocampo.validators``.
"""

import importlib
import sys

from . import config as _config


def main(argv=None):
    try:
        cfg = _config.load_config()
    except _config.ConfigError as e:
        print(f"preflight: {e}")
        return 1
    names = cfg.validators
    if not names:
        print("preflight: no validators configured.")
        return 0

    failed = []
    for name in names:
        print(f"\n=== {name} ===")
        try:
            mod = importlib.import_module(f"hipocampo.validators.{name}")
        except ModuleNotFoundError:
            print(f"SKIP (unknown validator '{name}')")
            continue
        try:
            rc = mod.main([])
        except _config.ConfigError as e:
            print(str(e))
            rc = 1
        if rc != 0:
            failed.append(name)
            print(f"FAILED ({name}, exit {rc})")
        else:
            print("OK")

    print("\n" + "=" * 46)
    if failed:
        print(f"{len(failed)} of {len(names)} validators FAILED: {', '.join(failed)}")
        return 1
    print(f"All {len(names)} validators passed. Safe to push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
