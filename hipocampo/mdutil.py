"""Shared markdown helpers — title extraction and ``.md`` file walking.

``search``, ``index`` and the capture-sweep hook each independently grew the same
two helpers (a frontmatter/heading title extractor and a recursive ``.md``
walker). They live here once so the three callers share one implementation.

Standard library only — keeps the zero-dependency promise.
"""

import os

__all__ = ["title_of", "iter_md", "iter_vault_md"]


def title_of(text, fallback):
    """Title of a note: first ``title:`` frontmatter value, else first ``# ``
    heading, else ``fallback``. Looks only at line starts, so prose mentioning
    ``# `` mid-document is ignored."""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("title:"):
            return line[len("title:"):].strip().strip("'\"")
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def iter_md(directory):
    """Yield every ``.md`` file path under ``directory`` (recursive).

    ``directory`` is any path-like; a path that is not a directory yields
    nothing. Filenames are sorted within each directory for deterministic order.
    """
    directory = os.fspath(directory)
    if not os.path.isdir(directory):
        return
    for dirpath, _sub, files in os.walk(directory):
        for fname in sorted(files):
            if fname.endswith(".md"):
                yield os.path.join(dirpath, fname)


def iter_vault_md(cfg, dirs):
    """Yield ``.md`` paths under each of ``dirs`` resolved against the vault root."""
    for d in dirs:
        yield from iter_md(cfg.vault_root / d)
