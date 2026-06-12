#!/usr/bin/env python3
"""Decay stale capture-sweep notes in the vault inbox.

The Stop hook (``capture-sweep``) drops auto-capture candidates into the inbox
(``<vault>/knowledge/_inbox/`` by default) for later triage. Un-triaged sweeps
that nobody moved to ``knowledge/`` or ``raw/sources/`` become noise. This
expires them after N days, preserving anything pinned (``pinned: true``) or
already moved past triage (``status != triage``).

Scope is deliberately narrow and safe: it only ever removes the ephemeral
auto-sweeps the kit itself generated (``type`` matching the configured sweep
type) that are provably stale — never human-authored knowledge notes, promoted
content, or anything pinned. The markdown stays the source of truth.

Everything project-specific (inbox location, decay window, sweep type) comes
from ``brain.config.toml``. Dry-run by default on the CLI; the Stop hook calls
``decay(apply=True)``. Standard library only.
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from . import config as _config
from .frontmatter import parse_frontmatter

_TRUTHY = {"true", "yes", "1", "sim"}


def find_stale(inbox_dir, sweep_type, days, today=None):
    """``[(path, age_days)]`` for un-triaged, un-pinned sweeps older than ``days``."""
    today = today or date.today()
    inbox_dir = Path(inbox_dir)
    stale = []
    if not inbox_dir.is_dir():
        return stale
    for path in sorted(inbox_dir.glob("*.md")):
        try:
            fields, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if fields.get("type") != sweep_type:
            continue  # only the ephemeral auto-sweeps; never human/knowledge notes
        if (fields.get("status") or "triage") != "triage":
            continue  # already triaged/promoted
        if str(fields.get("pinned", "")).strip().lower() in _TRUTHY:
            continue  # explicitly preserved
        try:
            age = (today - date.fromisoformat(fields.get("created", ""))).days
        except (ValueError, TypeError):
            continue  # no parseable date -> leave it alone
        if age > days:
            stale.append((str(path), age))
    return stale


def decay(cfg=None, days=None, apply=False, today=None):
    """Find stale sweeps; delete them when ``apply=True``. Returns the stale list."""
    cfg = cfg or _config.load_config()
    days = cfg.inbox_decay_days if days is None else days
    stale = find_stale(cfg.inbox_dir, cfg.inbox_sweep_type, days, today=today)
    if apply:
        for path, _age in stale:
            try:
                os.remove(path)
            except OSError:
                pass
    return stale


def main(argv=None):
    cfg = _config.load_config()
    ap = argparse.ArgumentParser(
        description="Expire stale capture-sweeps in the vault inbox."
    )
    ap.add_argument("--days", type=int, default=cfg.inbox_decay_days,
                    help=f"age threshold in days (default {cfg.inbox_decay_days})")
    ap.add_argument("--apply", action="store_true",
                    help="actually delete (default: dry-run)")
    args = ap.parse_args(argv)

    stale = decay(cfg=cfg, days=args.days, apply=args.apply)
    if not stale:
        print(f"inbox: no stale sweeps (> {args.days}d).")
        return 0
    verb = "removed" if args.apply else "stale"
    for path, age in stale:
        print(f"- {verb}: {os.path.relpath(path, cfg.repo_root)} ({age}d)")
    if not args.apply:
        print(f"\n{len(stale)} stale sweep(s). Run with --apply to remove.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
