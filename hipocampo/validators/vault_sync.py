#!/usr/bin/env python3
"""Vault consistency checks (frontmatter-as-truth + index-first reads).

Generic subset ported from the origin project:

- **knowledge index** — every ``knowledge/<area>/X.md`` has an entry in
  ``knowledge/index.md``, and every index link resolves (Karpathy LLM-wiki:
  agents must be able to discover a page without bulk-reading the vault).
- **status/area vocabulary** — pages under ``insights/`` use only the closed
  ``statuses``/``areas`` vocabularies from config (aliases are flagged).
- **provenance + staleness** — knowledge pages cite ``sources:`` that exist;
  pages older than ``stale_days`` and orphaned raw sources are warned.

Obsidian-dashboard-specific checks (Dataview view freshness, roadmap queue
drift, radar drift) are intentionally out of scope here. FAIL fails the run;
WARN is informational.
"""

import os
import re
import sys
from datetime import date

from .. import config as _config
from ..vault import load_pages, as_list


def check_knowledge_index(cfg):
    issues = []
    kroot = cfg.knowledge_dir
    index_path = kroot / "index.md"
    if not kroot.is_dir():
        return issues
    if not index_path.is_file():
        issues.append(("FAIL", "[Index] knowledge/index.md missing — required entry point for index-first reads"))
        return issues

    index_text = index_path.read_text(encoding="utf-8", errors="replace")
    # Strip HTML comments so commented-out examples don't count as real entries/links.
    index_text = re.sub(r"<!--.*?-->", "", index_text, flags=re.S)

    pages_on_disk = set()
    for area in sorted(os.listdir(kroot)):
        adir = kroot / area
        if not adir.is_dir() or area.startswith("_"):
            continue
        for fname in sorted(os.listdir(adir)):
            if fname.endswith(".md"):
                pages_on_disk.add(f"{area}/{fname}")

    for rel in sorted(pages_on_disk):
        slug = rel[:-3]
        if f"({rel})" not in index_text and f"({slug})" not in index_text:
            area = rel.split("/", 1)[0]
            issues.append(("FAIL", f"[Index] knowledge/{rel}: page has no entry in knowledge/index.md — add one line under area '{area}'"))

    for match in re.finditer(r"\]\(([^)]+\.md)\)", index_text):
        link = match.group(1)
        if link.startswith(("http://", "https://", "../")):
            continue
        target = (kroot / link).resolve()
        try:
            target.relative_to(kroot.resolve())
        except ValueError:
            continue
        if not target.is_file():
            issues.append(("FAIL", f"[Index] knowledge/index.md: link '{link}' points to a missing file"))

    return sorted(issues, key=lambda x: x[1])


def check_status_area(cfg):
    """Closed-vocabulary gate for insight pages. type=spec is skipped."""
    issues = []
    statuses = cfg.statuses
    areas = set(cfg.areas)
    aliases = cfg.area_aliases
    for page in load_pages(cfg.insights_dir):
        if page.fields.get("type") == "spec":
            continue
        status = (page.fields.get("status") or "").strip()
        if status and status not in statuses:
            issues.append(("FAIL", f"[Status] insights/{page.rel}: status={status!r} not in closed set ({'/'.join(sorted(statuses))})"))
        area = (page.fields.get("area") or "").strip()
        if area and area not in areas:
            if area in aliases:
                issues.append(("FAIL", f"[Area] insights/{page.rel}: area={area!r} is an alias of {aliases[area]!r} — normalize it"))
            else:
                issues.append(("FAIL", f"[Area] insights/{page.rel}: area={area!r} not in configured areas ({'/'.join(sorted(areas))})"))
    return sorted(issues, key=lambda x: x[1])


def check_provenance(cfg):
    """Knowledge-layer provenance + staleness."""
    issues = []
    kroot = cfg.knowledge_dir
    if not kroot.is_dir():
        return issues

    today = date.today()
    cited = set()
    for page in load_pages(kroot):
        if page.rel == "index.md":
            continue
        for src in as_list(page.fields.get("sources")):
            src = src.strip()
            if not src or src.startswith(("http://", "https://")):
                continue
            cited.add(os.path.normpath(src))
            if not (cfg.vault_root / src).is_file():
                issues.append(("FAIL", f"[Provenance] knowledge/{page.rel}: source not found '{src}'"))
        try:
            age = (today - date.fromisoformat(page.fields.get("updated", ""))).days
            if age > cfg.stale_days:
                issues.append(("WARN", f"[Staleness] knowledge/{page.rel}: updated {age} days ago (> {cfg.stale_days}) — review"))
        except (ValueError, TypeError):
            pass
        # Temporal validity: a page past its declared valid_until is expired.
        valid_until = (page.fields.get("valid_until") or "").strip()
        if valid_until:
            try:
                if date.fromisoformat(valid_until) < today:
                    issues.append(("WARN", f"[Expired] knowledge/{page.rel}: valid_until {valid_until} has passed — review or supersede"))
            except (ValueError, TypeError):
                pass

    sroot = cfg.raw_sources_dir
    raw_rel = cfg.raw_sources_dir.relative_to(cfg.vault_root).as_posix()
    if sroot.is_dir():
        for fname in sorted(os.listdir(sroot)):
            if fname.endswith(".md") and os.path.normpath(f"{raw_rel}/{fname}") not in cited:
                issues.append(("WARN", f"[Orphan] {raw_rel}/{fname}: no knowledge/ page cites this source"))

    return sorted(issues, key=lambda x: x[1])


def main(argv=None):
    cfg = _config.load_config()
    results = (check_knowledge_index(cfg)
               + check_status_area(cfg)
               + check_provenance(cfg))

    fails = [m for level, m in results if level == "FAIL"]
    warns = [m for level, m in results if level == "WARN"]

    for level, msg in results:
        print(f"{level}  {msg}")

    if fails:
        print(f"\nvalidate-vault-sync FAILED: {len(fails)} error(s), {len(warns)} warning(s).")
        return 1
    print(f"validate-vault-sync: OK ({len(warns)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
