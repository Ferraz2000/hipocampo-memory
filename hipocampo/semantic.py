#!/usr/bin/env python3
"""Optional local-embedding semantic search — the Phase 11 ``[semantic]`` tier.

Lazy and graceful by construction. The core never imports this module's heavy
dependencies; they load only when **all three** hold:

1. ``[semantic] enabled = true`` in ``brain.config.toml`` (off by default), and
2. the extra is installed (``model2vec`` + ``sqlite-vec`` — e.g.
   ``pip install model2vec sqlite-vec`` or a published ``hipocampo[semantic]``), and
3. this Python's ``sqlite3`` can load extensions (some macOS system Pythons /
   minimal Docker images disable it).

On any of those absent, :func:`available` is ``False`` and callers fall back to
pure BM25 — the tooling runs identically, just without the vector ranking. The
markdown vault stays the source of truth; vectors live in a disposable ``vec0``
table beside the FTS5 index and rebuild from disk.

The leaf functions that call ``model2vec``/``sqlite-vec`` (:func:`_load_model`,
:func:`_connect`, :func:`reindex`, :func:`rank`) run only when the extra is
installed; ``test_semantic.SemanticEndToEndTest`` exercises them end-to-end
wherever the deps exist (and ``skipUnless`` otherwise), while the availability /
fallback / RRF wiring is always covered by the stdlib suite.
"""

import os
import sqlite3
from functools import lru_cache

from . import config as _config

VEC_BASENAME = "vault-vectors.sqlite3"


def _deps():
    """Return the (model2vec, sqlite_vec) modules, or ``None`` if not installed."""
    try:
        import model2vec  # noqa: F401
        import sqlite_vec  # noqa: F401
        return model2vec, sqlite_vec
    except ImportError:
        return None


def extension_loadable():
    """True if this interpreter's sqlite3 can load extensions at all."""
    con = sqlite3.connect(":memory:")
    try:
        con.enable_load_extension(True)
        return True
    except (AttributeError, sqlite3.OperationalError):
        return False
    finally:
        con.close()


def available(cfg):
    """Whether the semantic ranking can run for this config + environment."""
    if os.environ.get("HIPOCAMPO_SEMANTIC", "1") == "0":
        return False
    return bool(cfg.semantic_enabled) and _deps() is not None and extension_loadable()


# --------------------------------------------------------------------------
# Dependency-backed leaf functions (only reached when `available()` is True)
# --------------------------------------------------------------------------

@lru_cache(maxsize=4)
def _load_model(name):
    from model2vec import StaticModel
    return StaticModel.from_pretrained(name)


def _embed(texts, cfg):
    """Embed strings → list of float vectors (model2vec static embeddings, CPU)."""
    vecs = _load_model(cfg.semantic_model).encode(list(texts))
    return [list(map(float, v)) for v in vecs]


def _connect(cfg):
    """Open the vec0 store, loading the sqlite-vec extension into the connection."""
    import sqlite_vec
    path = cfg.cache_dir / VEC_BASENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=10)
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    con.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS vec USING vec0("
        f"relpath TEXT PRIMARY KEY, embedding FLOAT[{cfg.semantic_dim}])")
    return con


def _serialize(vec):
    import sqlite_vec
    return sqlite_vec.serialize_float32(vec)


def reindex(cfg, items):
    """Embed and store ``items`` = iterable of ``(relpath, text)``. Replaces rows
    for the given relpaths so re-indexing a changed note is idempotent. No-op when
    the tier is unavailable. Returns the count embedded."""
    if not available(cfg):
        return 0
    items = list(items)
    if not items:
        return 0
    con = _connect(cfg)
    try:
        vecs = _embed([t for _, t in items], cfg)
        for (relpath, _text), vec in zip(items, vecs):
            con.execute("DELETE FROM vec WHERE relpath = ?", (relpath,))
            con.execute("INSERT INTO vec(relpath, embedding) VALUES(?, ?)",
                        (relpath, _serialize(vec)))
        con.commit()
        return len(items)
    finally:
        con.close()


def forget(cfg, relpaths):
    """Drop vectors for notes that vanished from disk. No-op when unavailable."""
    if not available(cfg):
        return 0
    relpaths = list(relpaths)
    if not relpaths:
        return 0
    con = _connect(cfg)
    try:
        con.executemany("DELETE FROM vec WHERE relpath = ?", [(r,) for r in relpaths])
        con.commit()
        return len(relpaths)
    finally:
        con.close()


def rank(query, cfg, limit=40):
    """Return ``[relpath, ...]`` best-first by vector similarity, or ``[]`` when the
    tier is unavailable or the store is empty. Pure ranking — fusion is the
    caller's job (``index.rrf_fuse``)."""
    if not available(cfg) or not query.strip():
        return []
    con = _connect(cfg)
    try:
        qvec = _embed([query], cfg)[0]
        rows = con.execute(
            "SELECT relpath FROM vec WHERE embedding MATCH ? "
            "ORDER BY distance LIMIT ?",
            (_serialize(qvec), limit),
        ).fetchall()
        return [r[0] for r in rows]
    except sqlite3.Error:
        return []  # never let a vec hiccup break search; BM25 already ran
    finally:
        con.close()


def main(argv=None):
    """`python -m hipocampo.semantic` — report tier status (diagnostic)."""
    cfg = _config.load_config()
    print(f"semantic.enabled (config): {cfg.semantic_enabled}")
    print(f"deps installed:            {_deps() is not None}")
    print(f"sqlite extension loadable: {extension_loadable()}")
    print(f"=> available:              {available(cfg)}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
