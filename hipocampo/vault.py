"""Lightweight vault page model — load markdown notes with their frontmatter.

This is the generic core that the validators build on (frontmatter-as-truth).
The heavier Dataview/DQL-to-markdown view machinery from the origin project is
deliberately deferred to a later, optional increment — it is the most
Obsidian-coupled layer and not needed for governance.
"""

from dataclasses import dataclass
from pathlib import Path

from .frontmatter import parse_frontmatter


@dataclass
class Page:
    path: Path        # absolute path on disk
    rel: str          # path relative to the scanned root, posix-style
    fields: dict      # parsed frontmatter


def load_pages(root, *, skip_underscore=True):
    """Load every ``*.md`` under ``root`` (recursively) as a :class:`Page`.

    Directories whose name starts with ``_`` (e.g. ``_inbox``) are skipped when
    ``skip_underscore`` is True. Returns ``[]`` if ``root`` does not exist.
    """
    root = Path(root)
    pages = []
    if not root.is_dir():
        return pages
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if skip_underscore and any(part.startswith("_") for part in rel.parts):
            continue
        try:
            fields, _ = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        pages.append(Page(path, rel.as_posix(), fields))
    return pages


def as_list(value):
    """Normalize a frontmatter value to a list (scalar -> single-item list)."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [value]
    return []
