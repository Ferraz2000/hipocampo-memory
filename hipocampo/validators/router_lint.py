#!/usr/bin/env python3
"""Router lint: keep AGENTS.md lean.

Long, vague instruction files measurably tax agent reasoning (Upsun/GitHub
research). This validator fails when the router exceeds the configured line cap,
nudging it back toward a short, operational form. Opt-in: add "router_lint" to
`validators` in brain.config.toml to enforce it.

Config: `[router]` { file = "AGENTS.md", max_lines = 120 }.
"""

import sys

from .. import config as _config


def check_router(cfg):
    path = cfg.repo_root / cfg.router_file
    if not path.is_file():
        return []  # nothing to lint
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    n = len(lines)
    if n > cfg.router_max_lines:
        return [("FAIL",
                 f"[Router] {cfg.router_file}: {n} lines (> {cfg.router_max_lines}) — "
                 f"trim to a lean, operational router (vague long files tax reasoning)")]
    return []


def main(argv=None):
    try:
        cfg = _config.load_config()
    except _config.ConfigError as e:
        print(f"router-lint: {e}")
        return 1
    issues = check_router(cfg)
    for level, msg in issues:
        print(f"{level}  {msg}")
    if any(level == "FAIL" for level, _ in issues):
        return 1
    print(f"router-lint: OK ({cfg.router_file} within {cfg.router_max_lines} lines).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
