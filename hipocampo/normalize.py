#!/usr/bin/env python3
"""Normalize frontmatter vocabulary across the vault's insights — the FIXER
counterpart to ``vault_sync`` (which only flags violations).

Two passes, both touching only the frontmatter block (body prose untouched):

1. Graded fields (impact/effort/risk/confidence) → canonical low/medium/high.
   Vaults historically mix locales and extra grades (baixo, médio, alta, small,
   large, none, ...); every dataview SORT relies on the 3-level scale.
2. ``area`` aliases → canonical, from ``[area_aliases]`` in brain.config.toml.
   ``type: spec`` keeps its own area vocabulary untouched.

Unknown values are left alone; ``vault_sync`` flags whatever stays off-vocab.

Usage:
  python -m hipocampo.normalize           # apply
  python -m hipocampo.normalize --check   # exit 1 if anything would change
"""

import os
import re
import sys

from . import config as _config

GRADE_FIELDS = ("impact", "effort", "risk", "confidence")
GRADE_SYNONYMS = {
    "low": "low", "baixo": "low", "baixa": "low", "small": "low",
    "very-low": "low", "none": "low",
    "medium": "medium", "medio": "medium", "médio": "medium",
    "media": "medium", "média": "medium", "variavel": "medium", "variável": "medium",
    "high": "high", "alto": "high", "alta": "high", "large": "high", "very-high": "high",
}

_FM_LINE = re.compile(r'^([A-Za-z0-9_]+):\s*"?([^"\n]*?)"?\s*$')


def normalize_text(text, area_aliases):
    """Return ``(new_text, changes)`` — changes = list of 'field: old -> new'."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text, []
    changes = []
    is_spec = False
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
        m = _FM_LINE.match(lines[i].rstrip("\n"))
        if m and m.group(1) == "type" and m.group(2).strip() == "spec":
            is_spec = True
    if end is None:
        return text, []

    for i in range(1, end):
        m = _FM_LINE.match(lines[i].rstrip("\n"))
        if not m:
            continue
        key, raw = m.group(1), m.group(2).strip()
        new = None
        if key in GRADE_FIELDS:
            canon = GRADE_SYNONYMS.get(raw.lower())
            if canon and canon != raw:
                new = canon
        elif key == "area" and not is_spec:
            canon = area_aliases.get(raw) or area_aliases.get(raw.lower())
            if canon and canon != raw:
                new = canon
        if new is not None:
            lines[i] = f"{key}: {new}\n"
            changes.append(f"{key}: {raw} -> {new}")
    return "".join(lines), changes


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    check = "--check" in argv
    try:
        cfg = _config.load_config()
    except _config.ConfigError as e:
        print(f"normalize: {e}")
        return 1

    touched = []
    root = cfg.insights_dir
    if root.is_dir():
        for path in sorted(root.rglob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            new, changes = normalize_text(text, cfg.area_aliases)
            if changes:
                touched.append((os.path.relpath(path, cfg.repo_root), changes))
                if not check:
                    path.write_text(new, encoding="utf-8")

    if not touched:
        print("normalize: nothing to change.")
        return 0
    verb = "would change" if check else "normalized"
    for rel, changes in touched:
        print(f"- {verb}: {rel} ({'; '.join(changes)})")
    return 1 if check else 0


if __name__ == "__main__":
    sys.exit(main())
