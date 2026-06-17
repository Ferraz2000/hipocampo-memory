#!/usr/bin/env python3
"""SQLite FTS5 index + link graph for the vault — optional search accelerator.

``search.py`` re-reads and re-tokenizes the whole corpus on every call. This
module persists a full-text index (incremental, keyed by mtime+size) under the
configured cache dir so only changed files are re-indexed, and adds **RRF**
(Reciprocal Rank Fusion) of the keyword ranking with graph-neighbor expansion:
a note linked from a strong hit can surface even without the query terms.

Standard library only (``sqlite3`` with FTS5). The index is a pure derived
artifact:

- It is always safe to delete (cold build on next call).
- A schema-version bump drops and rebuilds automatically.
- If FTS5 is not compiled into the local sqlite, :func:`fts5_available` returns
  False and callers fall back to the pure-Python BM25 path — the tooling runs
  identically headless/CI/local, just without the speedup.

Set ``HIPOCAMPO_VAULT_INDEX=0`` to bypass the index entirely. Everything
project-specific (vault location, cache path, searched dirs) comes from
``brain.config.toml``.
"""

import os
import re
import sqlite3
from pathlib import Path

from . import config as _config
from . import semantic as _semantic
from .mdutil import iter_vault_md
from .mdutil import title_of as extract_title  # back-compat alias

_SCHEMA_VERSION = 1
INDEX_BASENAME = "vault-index.sqlite3"

# .md references anywhere in a note (markdown links + frontmatter path fields).
_MD_REF_RE = re.compile(r"([\w\-./]+\.md)")
_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


def index_enabled():
    return os.environ.get("HIPOCAMPO_VAULT_INDEX", "1") != "0"


def fts5_available():
    """True if this sqlite build can create FTS5 virtual tables."""
    try:
        con = sqlite3.connect(":memory:")
        try:
            con.execute("CREATE VIRTUAL TABLE _probe USING fts5(x)")
            return True
        finally:
            con.close()
    except sqlite3.Error:
        return False


# --------------------------------------------------------------------------
# Extraction helpers (pure)
# --------------------------------------------------------------------------

def extract_links(text, note_relpath, repo_root):
    """Repo-relative .md targets referenced by ``note_relpath`` that exist on disk.

    Resolves each relative reference against the note's directory; keeps only
    targets that actually resolve to a file. Over-broad matches (a ``.md``
    mentioned in prose) simply fail the existence check.
    """
    repo_root = str(repo_root)
    note_dir = os.path.dirname(os.path.join(repo_root, note_relpath))
    out = set()
    for ref in _MD_REF_RE.findall(text):
        target = os.path.normpath(os.path.join(note_dir, ref))
        if os.path.isfile(target):
            rel = os.path.relpath(target, repo_root).replace(os.sep, "/")
            if rel != note_relpath:
                out.add(rel)
    return sorted(out)


def rrf_fuse(rank_lists, k=60):
    """Reciprocal Rank Fusion of several ranked lists (best-first).

    Returns ``(ordered_items, score_map)``. Pure function — no I/O.
    """
    scores = {}
    for lst in rank_lists:
        for rank, item in enumerate(lst):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank + 1)
    ordered = sorted(scores, key=lambda d: scores[d], reverse=True)
    return ordered, scores


# --------------------------------------------------------------------------
# Index lifecycle
# --------------------------------------------------------------------------

def _index_file(cfg):
    return cfg.cache_dir / INDEX_BASENAME


def _connect(cfg):
    index_file = _index_file(cfg)
    index_file.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(index_file), timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    return con


def _ensure_schema(con):
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='meta'"
    ).fetchone()
    version = None
    if row:
        v = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        version = int(v[0]) if v else None
    if version != _SCHEMA_VERSION:
        for tbl in ("notes", "files", "edges", "meta"):
            con.execute(f"DROP TABLE IF EXISTS {tbl}")
        con.execute(
            "CREATE VIRTUAL TABLE notes USING fts5("
            "relpath UNINDEXED, title, body, "
            "tokenize='unicode61 remove_diacritics 2')"
        )
        con.execute(
            "CREATE TABLE files(path TEXT PRIMARY KEY, mtime_ns INTEGER, "
            "size INTEGER, relpath TEXT, rowid_ref INTEGER)"
        )
        con.execute("CREATE TABLE edges(src TEXT, dst TEXT)")
        con.execute("CREATE INDEX idx_edges_src ON edges(src)")
        con.execute("CREATE INDEX idx_edges_dst ON edges(dst)")
        con.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)")
        con.execute(
            "INSERT INTO meta(key, value) VALUES('schema_version', ?)",
            (str(_SCHEMA_VERSION),),
        )
        con.commit()


def refresh(con, cfg, dirs=None):
    """Incrementally bring the index in sync with disk. Returns count reindexed."""
    dirs = dirs or cfg.search_dirs
    repo_root = str(cfg.repo_root)
    _ensure_schema(con)
    seen = set()
    reindexed = 0
    embed_items = []   # (relpath, text) of (re)indexed notes for the [semantic] tier
    forget_paths = []  # relpaths pruned from disk, to drop from the vector store
    known = {
        row[0]: (row[1], row[2], row[3])
        for row in con.execute("SELECT path, mtime_ns, size, rowid_ref FROM files")
    }
    for path in iter_vault_md(cfg, dirs):
        seen.add(path)
        try:
            st = os.stat(path)
        except OSError:
            continue
        prev = known.get(path)
        if prev and prev[0] == st.st_mtime_ns and prev[1] == st.st_size:
            continue  # unchanged
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        relpath = os.path.relpath(path, repo_root).replace(os.sep, "/")
        title = extract_title(text, os.path.basename(path))
        if prev:  # changed: drop old FTS row + edges first
            con.execute("DELETE FROM notes WHERE rowid=?", (prev[2],))
            con.execute("DELETE FROM edges WHERE src=?", (relpath,))
        cur = con.execute(
            "INSERT INTO notes(relpath, title, body) VALUES(?,?,?)",
            (relpath, title, text),
        )
        rowid = cur.lastrowid
        con.execute(
            "INSERT OR REPLACE INTO files(path, mtime_ns, size, relpath, rowid_ref) "
            "VALUES(?,?,?,?,?)",
            (path, st.st_mtime_ns, st.st_size, relpath, rowid),
        )
        for dst in extract_links(text, relpath, repo_root):
            con.execute("INSERT INTO edges(src, dst) VALUES(?,?)", (relpath, dst))
        embed_items.append((relpath, text))
        reindexed += 1
    # Prune files that vanished from disk.
    for path, meta in known.items():
        if path not in seen:
            con.execute("DELETE FROM notes WHERE rowid=?", (meta[2],))
            relrow = con.execute("SELECT relpath FROM files WHERE path=?", (path,)).fetchone()
            if relrow:
                con.execute("DELETE FROM edges WHERE src=?", (relrow[0],))
                forget_paths.append(relrow[0])
            con.execute("DELETE FROM files WHERE path=?", (path,))
    con.commit()
    # Mirror the same delta into the optional vector store (no-op unless the
    # [semantic] tier is available). Best-effort: never let it break indexing.
    try:
        _semantic.reindex(cfg, embed_items)
        _semantic.forget(cfg, forget_paths)
    except Exception:
        pass
    return reindexed


# --------------------------------------------------------------------------
# Query
# --------------------------------------------------------------------------

def _match_expr(query):
    terms = _TOKEN_RE.findall(query.lower())
    if not terms:
        return None
    return " OR ".join('"%s"' % t for t in terms)


def _neighbors(con, relpath):
    rows = con.execute(
        "SELECT dst FROM edges WHERE src=? UNION SELECT src FROM edges WHERE dst=?",
        (relpath, relpath),
    ).fetchall()
    return [r[0] for r in rows]


def search(query, cfg=None, top=8, dirs=None, rrf=True):
    """Search the index. Returns ``[(relpath, score), ...]`` best-first.

    With ``rrf=True`` the FTS5 ranking is fused with graph-neighbor expansion so
    notes linked from strong hits can surface. Raises ``sqlite3.Error`` if FTS5
    is unavailable — callers should check :func:`fts5_available` first and fall
    back to the pure-Python path in ``search.py``.
    """
    cfg = cfg or _config.load_config()
    expr = _match_expr(query)
    if expr is None:
        return []
    con = _connect(cfg)
    try:
        refresh(con, cfg, dirs=dirs)
        rows = con.execute(
            "SELECT relpath, bm25(notes, 1.0, 5.0, 1.0) AS rank "
            "FROM notes WHERE notes MATCH ? ORDER BY rank LIMIT ?",
            (expr, top * 5),
        ).fetchall()
        prefixes = None
        if dirs:
            base = cfg.vault_rel
            prefixes = tuple(f"{base}/{d.replace(os.sep, '/')}" for d in dirs)
        fts = [rp for rp, _ in rows if not prefixes or rp.startswith(prefixes)]

        if not rrf:
            return [(rp, 1.0 / (i + 1)) for i, rp in enumerate(fts)][:top]

        # Graph list: neighbors of the top FTS hits, ranked by aggregated source rank.
        neigh = {}
        for rank, rp in enumerate(fts[:10]):
            for nb in _neighbors(con, rp):
                if prefixes and not nb.startswith(prefixes):
                    continue
                neigh[nb] = neigh.get(nb, 0.0) + 1.0 / (60 + rank + 1)
        neigh_list = sorted(neigh, key=lambda d: neigh[d], reverse=True)

        rank_lists = [fts, neigh_list]
        # [semantic] tier: fuse a local-embedding vector ranking when available
        # (off ⇒ this is empty and RRF degenerates to today's FTS+graph result).
        if _semantic.available(cfg):
            vec = [rp for rp in _semantic.rank(query, cfg, limit=top * 5)
                   if not prefixes or rp.startswith(prefixes)]
            if vec:
                rank_lists.append(vec)

        ordered, scores = rrf_fuse(rank_lists)
        return [(rp, scores[rp]) for rp in ordered][:top]
    finally:
        con.close()


def main(argv=None):
    import argparse

    cfg = _config.load_config()
    ap = argparse.ArgumentParser(description="Vault FTS5 index (build / query).")
    ap.add_argument("query", nargs="?", help="search terms (empty = rebuild only)")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--dir", action="append")
    ap.add_argument("--no-rrf", action="store_true")
    args = ap.parse_args(argv)

    if not fts5_available():
        raise SystemExit("FTS5 unavailable in this sqlite — use search.py (pure BM25).")

    if not args.query:
        con = _connect(cfg)
        try:
            n = refresh(con, cfg, dirs=args.dir)
        finally:
            con.close()
        print(f"index refreshed ({n} note(s) reindexed).")
        return 0
    for rp, score in search(args.query, cfg=cfg, top=args.top, dirs=args.dir, rrf=not args.no_rrf):
        print(f"[{score:.4f}] {rp}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
