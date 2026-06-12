"""Parse a leading YAML-ish frontmatter block from a markdown file.

Vendored generic core (no project-specifics). Only the structures the vault
actually uses are supported: top-level ``key: value`` scalars and ``key:``
followed by ``  - item`` list entries. Quotes and surrounding whitespace are
stripped. Standard library only — deliberately not a full YAML parser, so the
kit keeps its zero-dependency promise.
"""

import re

_FM_DELIM = "---"


def parse_frontmatter(text):
    """Return ``(fields, body)`` for ``text``.

    ``fields`` is a dict of the frontmatter; ``body`` is everything after the
    closing delimiter. If there is no frontmatter, returns ``({}, text)``.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FM_DELIM:
        return {}, text

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _FM_DELIM:
            end = i
            break
    if end is None:
        return {}, text

    fields = {}
    pending_key = None
    for raw in lines[1:end]:
        list_match = re.match(r"\s+-\s+(.*)$", raw)
        if list_match and pending_key is not None:
            if not isinstance(fields.get(pending_key), list):
                fields[pending_key] = []
            fields[pending_key].append(_clean(list_match.group(1)))
            continue

        kv = re.match(r"([A-Za-z0-9_]+):\s*(.*)$", raw)
        if not kv:
            continue
        key, value = kv.group(1), kv.group(2)
        if value.strip() == "":
            # Could be an empty scalar or the head of a list block.
            fields[key] = ""
            pending_key = key
        else:
            fields[key] = _clean(value)
            pending_key = None

    body = "\n".join(lines[end + 1:])
    if text.endswith("\n"):
        body += "\n"
    return fields, body


def _clean(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value.strip()
