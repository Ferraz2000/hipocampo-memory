#!/usr/bin/env python3
"""Materialize the vault's Dataview views into ``<vault>/_generated/``.

Dataview blocks only render inside Obsidian; headless agents read raw Markdown.
This executes each ```` ```dataview ```` block against note frontmatter (the
single source of truth) and writes a static Markdown mirror that agents — and
GitHub readers — can consume. Frontmatter-as-truth: the generated files are a
read-model, never hand-edited.

Supported DQL subset (what real dashboards use): ``TABLE [WITHOUT ID]`` /
``LIST``, ``FROM "<path>"``, ``WHERE`` (=, !=, !, AND, OR, parentheses, truthy
field), ``GROUP BY``, ``SORT field [ASC|DESC]`` (grade fields rank
low<medium<high; ``*_at`` fields sort as dates), ``LIMIT``, and in grouped
tables the aggregates ``length(rows)`` and
``filter(rows, (r) => r.field = "value")``.

Everything project-specific comes from ``brain.config.toml``: the vault root and
``[views] notes_root`` (vault-relative directory whose notes feed the queries;
default ``insights``).

Usage:
  python -m hipocampo.views           # write/update the generated mirrors
  python -m hipocampo.views --check   # exit 1 if anything is stale
"""

import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import config as _config
from .frontmatter import parse_frontmatter

GRADE_FIELDS = ("impact", "effort", "risk", "confidence")
_RANK = {"high": 3, "medium": 2, "low": 1}


# --------------------------------------------------------------------------
# Notes (the rows queries run against)
# --------------------------------------------------------------------------

@dataclass
class Note:
    path: str          # absolute path
    name: str          # filename without extension
    rel_dir: str       # directory relative to the notes root, posix-style
    fields: dict = field(default_factory=dict)

    def get(self, key, default=""):
        return self.fields.get(key, default)


def load_notes(root):
    """Every ``*.md`` under ``root`` as a :class:`Note` (skips ``_``-dirs)."""
    root = Path(root)
    notes = []
    if not root.is_dir():
        return notes
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if any(part.startswith("_") for part in rel.parts):
            continue
        try:
            fields, _body = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        notes.append(Note(str(path), path.stem, rel.parent.as_posix().replace(".", ""), fields))
    notes.sort(key=lambda n: (n.rel_dir, n.name))
    return notes


# --------------------------------------------------------------------------
# DQL parsing
# --------------------------------------------------------------------------

@dataclass
class Column:
    expr: str
    label: str


@dataclass
class Query:
    kind: str          # "table" | "list"
    without_id: bool
    columns: list
    from_path: str
    where: object
    sort: list
    limit: int
    group_by: str


@dataclass
class Group:
    key: str
    rows: list


def _split_top(text, sep=","):
    parts, depth, cur = [], 0, ""
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return parts


def _parse_columns(header):
    cols = []
    for piece in _split_top(header):
        piece = piece.strip().rstrip(",").strip()
        if not piece:
            continue
        m = re.match(r'(?is)^(.*?)\s+as\s+"([^"]*)"\s*$', piece)
        if m:
            cols.append(Column(m.group(1).strip(), m.group(2)))
        else:
            cols.append(Column(piece, piece))
    return cols


def _tokenize_where(text):
    return re.findall(r'\(|\)|!=|=|!|"[^"]*"|[A-Za-z0-9_.]+', text)


def _parse_where(text):
    if not text or not text.strip():
        return None
    toks = _tokenize_where(text)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def nxt():
        t = peek()
        pos[0] += 1
        return t

    def p_or():
        node = p_and()
        while peek() and peek().upper() == "OR":
            nxt()
            node = ("or", node, p_and())
        return node

    def p_and():
        node = p_atom()
        while peek() and peek().upper() == "AND":
            nxt()
            node = ("and", node, p_atom())
        return node

    def p_atom():
        t = peek()
        if t == "(":
            nxt()
            e = p_or()
            if peek() == ")":
                nxt()
            return e
        if t == "!":
            nxt()
            return ("not", ("truthy", nxt()))
        f = nxt()
        if peek() in ("=", "!="):
            op = nxt()
            val = nxt() or ""
            if val.startswith('"'):
                val = val[1:-1]
            return ("cmp", f, op, val)
        return ("truthy", f)

    return p_or()


def _parse_sort(text):
    out = []
    for piece in _split_top(text):
        piece = piece.strip()
        if not piece:
            continue
        parts = piece.split()
        out.append((parts[0], parts[1].upper() if len(parts) > 1 else "ASC"))
    return out


def parse_dql(text):
    t = text.strip()
    kind = "list" if re.match(r"(?is)^LIST\b", t) else "table"
    without_id = bool(re.search(r"(?is)^TABLE\s+WITHOUT\s+ID\b", t))

    keywords = ["FROM", "WHERE", "GROUP BY", "SORT", "LIMIT", "FLATTEN"]
    found = {}
    for kw in keywords:
        m = re.search(r"(?i)\b" + kw.replace(" ", r"\s+") + r"\b", t)
        if m:
            found[kw] = (m.start(), m.end())

    def section(kw):
        if kw not in found:
            return None
        start = found[kw][1]
        later = [found[k][0] for k in keywords if k in found and found[k][0] > found[kw][0]]
        return t[start:(min(later) if later else len(t))].strip()

    header_end = found["FROM"][0] if "FROM" in found else len(t)
    header = re.sub(r"(?is)^\s*(TABLE\s+WITHOUT\s+ID|TABLE|LIST)", "", t[:header_end])
    columns = _parse_columns(header) if kind == "table" else []

    from_path = None
    if "FROM" in found:
        fm = re.search(r'"([^"]+)"', section("FROM") or "")
        from_path = fm.group(1) if fm else None

    where = _parse_where(section("WHERE")) if "WHERE" in found else None
    group_by = section("GROUP BY") if "GROUP BY" in found else None
    sort = _parse_sort(section("SORT")) if "SORT" in found else []

    limit = None
    if "LIMIT" in found:
        lm = re.search(r"\d+", section("LIMIT") or "")
        limit = int(lm.group()) if lm else None

    return Query(kind, without_id, columns, from_path, where, sort, limit, group_by)


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------

def _value_of(note, field_name):
    if field_name == "file.name":
        return note.name
    return note.get(field_name)


def _eval(node, note):
    if node is None:
        return True
    op = node[0]
    if op == "and":
        return _eval(node[1], note) and _eval(node[2], note)
    if op == "or":
        return _eval(node[1], note) or _eval(node[2], note)
    if op == "not":
        return not _eval(node[1], note)
    if op == "truthy":
        v = _value_of(note, node[1])
        return bool(v) and v != ""
    if op == "cmp":
        _, fname, comp, val = node
        v = _value_of(note, fname)
        return (v == val) if comp == "=" else (v != val)
    return True


def _from_filter(query, notes, notes_root):
    fp = query.from_path or notes_root
    if fp == notes_root:
        return list(notes)
    if fp.startswith(notes_root + "/"):
        sub = fp[len(notes_root) + 1:]
        return [n for n in notes if n.rel_dir == sub or n.rel_dir.startswith(sub + "/")]
    return list(notes)


def _sort_key(field_name):
    def key(n):
        if field_name == "file.name":
            return n.name
        if field_name in GRADE_FIELDS:
            return _RANK.get(str(n.get(field_name)).strip().lower(), 0)
        if field_name.endswith("_at"):
            try:
                return date.fromisoformat(n.get(field_name))
            except (ValueError, TypeError):
                return date.min
        return n.get(field_name) or ""
    return key


def execute(query, notes, notes_root="insights"):
    rows = [n for n in _from_filter(query, notes, notes_root) if _eval(query.where, n)]

    if query.group_by:
        groups = {}
        for n in rows:
            groups.setdefault(n.get(query.group_by) or "", []).append(n)
        glist = [Group(k, v) for k, v in groups.items()]
        for field_name, direction in reversed(query.sort or []):
            if field_name == query.group_by:
                glist.sort(key=lambda g: g.key, reverse=(direction == "DESC"))
            elif field_name.startswith("length"):
                glist.sort(key=lambda g: len(g.rows), reverse=(direction == "DESC"))
        if query.limit:
            glist = glist[:query.limit]
        return glist

    for field_name, direction in reversed(query.sort or []):
        rows.sort(key=_sort_key(field_name), reverse=(direction == "DESC"))
    if query.limit:
        rows = rows[:query.limit]
    return rows


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

_FILTER_RE = re.compile(r'filter\(rows,\s*\(r\)\s*=>\s*r\.(\w+)\s*(!?=)\s*"([^"]*)"\)')


def _link(note, prefix):
    sub = (note.rel_dir + "/") if note.rel_dir else ""
    return f"[{note.name}]({prefix}/{sub}{note.name}.md)"


def _cell(value):
    if value is None:
        value = ""
    elif isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    else:
        value = str(value)
    value = value.replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip()
    return value if value != "" else "—"


def _table_md(header, body):
    if not body:
        return "_none_"
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for row in body:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def render(query, rows, link_prefix, id_label="Note"):
    if query.kind == "list":
        if not rows:
            return "_none_"
        return "\n".join(f"- {_link(n, link_prefix)}" for n in rows)

    labels = [c.label for c in query.columns]

    if query.group_by:
        body = []
        for g in rows:
            cells = []
            for c in query.columns:
                e = c.expr.strip()
                if e == query.group_by:
                    cells.append(_cell(g.key))
                elif re.match(r"length\(\s*rows\s*\)", e):
                    cells.append(str(len(g.rows)))
                else:
                    m = _FILTER_RE.search(e)
                    if m:
                        fld, comp, val = m.group(1), m.group(2), m.group(3)
                        cells.append(str(sum(
                            1 for n in g.rows
                            if ((n.get(fld) == val) if comp == "=" else (n.get(fld) != val))
                        )))
                    else:
                        cells.append("")
            body.append(cells)
        return _table_md(labels, body)

    header = ([id_label] if not query.without_id else []) + labels
    body = []
    for n in rows:
        cells = [_link(n, link_prefix)] if not query.without_id else []
        for c in query.columns:
            e = c.expr.strip()
            cells.append(_cell(n.name if e == "file.name" else n.get(e)))
        body.append(cells)
    return _table_md(header, body)


# --------------------------------------------------------------------------
# Source discovery + materialization
# --------------------------------------------------------------------------

def iter_dataview_blocks(text):
    """Yield ``(nearest_heading, query_text)`` for each ```dataview block."""
    lines = text.splitlines()
    heading = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        h = re.match(r"^#{1,6}\s+(.*)$", line)
        if h:
            heading = h.group(1).strip()
        if line.strip().startswith("```dataview"):
            j = i + 1
            buf = []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                buf.append(lines[j])
                j += 1
            yield heading, "\n".join(buf)
            i = j + 1
            continue
        i += 1


_GEN_BANNER = (
    "<!-- AUTO-GENERATED by `python -m hipocampo.views` — DO NOT EDIT BY HAND.\n"
    "     Source of truth: note frontmatter + the dataview blocks in {source}.\n"
    "     Regenerate with: python -m hipocampo.views -->"
)


def generate_for_source(source_text, notes, notes_root, link_prefix, source_name, id_label="Note"):
    parts = [
        _GEN_BANNER.format(source=source_name),
        "",
        f"# Materialized views — `{source_name}`",
        "",
        "Headless mirror of the `dataview` blocks (which only render inside "
        "Obsidian). Agents read this file; humans edit the source.",
        "",
    ]
    for heading, qtext in iter_dataview_blocks(source_text):
        query = parse_dql(qtext)
        rendered = render(query, execute(query, notes, notes_root), link_prefix, id_label)
        parts.append(f"## {heading or '(untitled)'}")
        parts.append("")
        parts.append(rendered)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def discover_sources(vault):
    """Markdown files under the vault carrying ```dataview blocks (excl. _generated)."""
    found = []
    for dirpath, _dirs, files in os.walk(vault):
        if os.sep + "_generated" in dirpath + os.sep:
            continue
        for fname in files:
            if not fname.endswith(".md"):
                continue
            path = os.path.join(dirpath, fname)
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                if "```dataview" in fh.read():
                    found.append(path)
    found.sort()
    return found


def build_all(cfg):
    """Map of generated-file-path -> content, for every dataview source."""
    vault = str(cfg.vault_root)
    notes_root = cfg.views_notes_root
    notes = load_notes(cfg.vault_root / notes_root)
    link_prefix = "../" + notes_root
    out = {}
    for src in discover_sources(vault):
        with open(src, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        gen = os.path.join(vault, "_generated", os.path.basename(src))
        out[gen] = generate_for_source(text, notes, notes_root, link_prefix,
                                       os.path.basename(src), cfg.views_id_label)
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    check = "--check" in argv
    try:
        cfg = _config.load_config()
    except _config.ConfigError as e:
        print(f"views: {e}")
        return 1

    built = build_all(cfg)
    changed = []
    for path, content in sorted(built.items()):
        existing = None
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                existing = fh.read()
        if existing != content:
            changed.append(path)
            if not check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(content)

    rel = sorted(os.path.relpath(p, cfg.repo_root) for p in changed)
    if check:
        if changed:
            print("Stale materialized views:")
            for r in rel:
                print(f"  - {r}")
            print("Run: python -m hipocampo.views")
            return 1
        print(f"Materialized views OK ({len(built)} file(s)).")
        return 0

    if changed:
        print(f"Regenerated {len(changed)} of {len(built)} view(s):")
        for r in rel:
            print(f"  - {r}")
    else:
        print(f"Nothing to do; {len(built)} view(s) up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
