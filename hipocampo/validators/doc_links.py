#!/usr/bin/env python3
"""Validate docs: configured required docs must exist, and every relative
Markdown link in the repo must resolve.

``required_docs`` is a contract (routing depends on those paths); the link scan
is derived from all ``.md`` files. Both come from ``brain.config.toml``.
"""

import os
import re
import sys

from .. import config as _config

_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_ALWAYS_EXCLUDE = {".git", "__pycache__"}


def missing_required_docs(repo_root, required):
    return [d for d in required if not os.path.exists(os.path.join(repo_root, d))]


def broken_doc_links(repo_root, exclude_dirs=None):
    """Relative Markdown links that don't resolve. Skips code fences,
    external/anchor links, and the excluded (build/vendor/cache) dirs.
    Returns ``(file, target)``."""
    repo_root = str(repo_root)
    exclude = _ALWAYS_EXCLUDE | set(exclude_dirs or ())
    issues = []
    for dirpath, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in exclude]
        for fname in files:
            if not fname.endswith(".md"):
                continue
            full = os.path.join(dirpath, fname)
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            # Strip HTML comments so commented-out example links aren't validated.
            text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
            in_fence = False
            for line in text.splitlines():
                if line.lstrip().startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                for m in _LINK_RE.finditer(line):
                    target = m.group(1).strip()
                    if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                        continue
                    # Skip placeholder links in docs/skill templates, e.g.
                    # `[<slug>](<area>/<slug>.md)` or `[<title>](<path>)`. Angle
                    # brackets can't appear in a real relative path, so a target
                    # carrying one is an illustrative format string, not a link.
                    if "<" in target or ">" in target:
                        continue
                    path_only = target.split("#", 1)[0]
                    if not path_only:
                        continue
                    if not os.path.exists(os.path.join(dirpath, path_only)):
                        issues.append((os.path.relpath(full, repo_root), target))
    return issues


def main(argv=None):
    try:
        cfg = _config.load_config()
    except _config.ConfigError as e:
        print(f"doc-links: {e}")
        return 1
    exclude = set(cfg.doc_links_exclude_dirs) | {cfg.cache_dir.name}
    missing = missing_required_docs(cfg.repo_root, cfg.required_docs)
    broken = broken_doc_links(cfg.repo_root, exclude)

    for d in missing:
        print(f"FAIL  required doc missing: {d}")
    for f, target in broken:
        print(f"FAIL  broken link in {f}: '{target}'")

    if missing or broken:
        print(f"\nvalidate-doc-links FAILED: {len(missing)} missing doc(s), {len(broken)} broken link(s).")
        return 1
    print("Documentation link validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
