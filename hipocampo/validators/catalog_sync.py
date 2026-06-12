#!/usr/bin/env python3
"""Curated-catalog ↔ disk sync (opt-in): skills bundles and instruction files.

Two drift classes that silently rot multi-agent repos:

1. **Skills catalog** — every depth-1 ``<skills_dir>/<name>/SKILL.md`` bundle
   must have frontmatter ``name`` matching its directory, a ``description``,
   and a token mention in the catalog doc; reverse, every id in the catalog's
   markdown table must have a bundle on disk (catches renamed/deleted skills).
2. **Required instruction files** — a deliberate, curated list (e.g. subtree
   ``AGENTS.md`` files) that must exist and stay concise. Not derivable from
   disk: the list IS the contract (catches a deleted/moved subtree router).
   The root router's size is ``router_lint``'s job and is skipped here.

Config (``[catalog]`` in brain.config.toml; empty lists = checks skipped):
  skills_dirs = [".claude/skills"]
  catalog_doc = "SKILLS.md"
  required_files = ["AGENTS.md", "src/api/AGENTS.md", ...]
  required_files_max_lines = 80   # 0 = no size cap

Add ``"catalog_sync"`` to ``validators`` to enforce.
"""

import os
import re
import sys
from dataclasses import dataclass

from .. import config as _config
from ..frontmatter import parse_frontmatter

_CATALOG_ROW_RE = re.compile(r"^\s*\|\s*`([a-z][a-z0-9-]+)`")


@dataclass
class SkillBundle:
    name: str
    path: str
    fm_name: str
    has_description: bool


def discover_skill_bundles(skills_dir):
    """Every depth-1 ``<skills_dir>/<name>/SKILL.md`` (nested/archived ignored)."""
    bundles = []
    if not os.path.isdir(skills_dir):
        return bundles
    for entry in sorted(os.listdir(skills_dir)):
        skill_md = os.path.join(skills_dir, entry, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        with open(skill_md, "r", encoding="utf-8", errors="replace") as fh:
            fields, _ = parse_frontmatter(fh.read())
        bundles.append(SkillBundle(entry, skill_md, fields.get("name", ""),
                                   bool(fields.get("description"))))
    return bundles


def skill_catalog_violations(bundles, catalog_text):
    issues = []
    for b in bundles:
        if b.fm_name != b.name:
            issues.append((b.name, f"frontmatter name={b.fm_name!r} != directory {b.name!r}"))
        if not b.has_description:
            issues.append((b.name, "frontmatter missing description"))
        token = re.compile(r"(?<![\w-])" + re.escape(b.name) + r"(?![\w-])")
        if not token.search(catalog_text):
            issues.append((b.name, "not listed in the catalog doc"))
    return issues


def catalog_table_skills(catalog_text):
    """Skill ids in the first column of the catalog's markdown table rows."""
    return [m.group(1) for line in catalog_text.splitlines()
            if (m := _CATALOG_ROW_RE.match(line))]


def required_files_violations(repo_root, required, max_lines, skip_cap_for=None):
    issues = []
    for rel in required:
        path = os.path.join(repo_root, rel)
        if not os.path.isfile(path):
            issues.append(f"required file missing: {rel}")
            continue
        if max_lines and rel != skip_cap_for:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                n = len(fh.read().splitlines())
            if n > max_lines:
                issues.append(f"{rel}: {n} lines (> {max_lines}) — keep it concise")
    return issues


def main(argv=None):
    try:
        cfg = _config.load_config()
    except _config.ConfigError as e:
        print(f"catalog-sync: {e}")
        return 1

    issues = []

    # 1) skills bundles ↔ catalog doc
    catalog_doc = cfg.catalog_doc
    catalog_text = None
    if cfg.catalog_skills_dirs:
        if catalog_doc:
            cpath = cfg.repo_root / catalog_doc
            if not cpath.is_file():
                issues.append(("catalog", f"catalog doc missing: {catalog_doc}"))
            else:
                catalog_text = cpath.read_text(encoding="utf-8", errors="replace")
        all_bundle_names = []
        for d in cfg.catalog_skills_dirs:
            bundles = discover_skill_bundles(str(cfg.repo_root / d))
            all_bundle_names += [b.name for b in bundles]
            if catalog_text is not None:
                issues += skill_catalog_violations(bundles, catalog_text)
            else:  # no catalog doc configured: structural checks only
                for b in bundles:
                    if b.fm_name != b.name:
                        issues.append((b.name, f"frontmatter name={b.fm_name!r} != directory {b.name!r}"))
                    if not b.has_description:
                        issues.append((b.name, "frontmatter missing description"))
        if catalog_text is not None:
            for orphan in catalog_table_skills(catalog_text):
                if orphan not in all_bundle_names:
                    issues.append(("catalog", f"'{orphan}' is in the catalog table but has no bundle on disk"))

    # 2) curated required files
    for m in required_files_violations(str(cfg.repo_root), cfg.catalog_required_files,
                                       cfg.catalog_required_files_max_lines,
                                       skip_cap_for=cfg.router_file):
        issues.append(("files", m))

    for name, msg in issues:
        print(f"FAIL  [{name}] {msg}")
    if issues:
        print(f"\ncatalog-sync FAILED: {len(issues)} violation(s).")
        return 1
    print("catalog-sync: OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
