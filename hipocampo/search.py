#!/usr/bin/env python3
"""Keyword search over the vault — pure stdlib, zero dependencies.

Ranks notes under the configured search dirs (knowledge / insights / specs /
raw/sources by default) by BM25 relevance to the query. This is the headless
"Query" path of the hybrid model: it runs identically in a remote agent
session, in CI, and on a local machine, with no external index required.

When the optional FTS5 index (``index.py``) is available it is used as a fast
path (with RRF graph expansion); otherwise this falls back to re-tokenizing the
corpus in pure Python. Everything project-specific comes from
``brain.config.toml``.

Usage:
  python -m hipocampo.search "store onboarding"
  python -m hipocampo.search "model collapse" --top 5
  python -m hipocampo.search "capture" --dir knowledge
"""

import argparse
import math
import os
import re
import sys
import unicodedata

from . import config as _config
from .mdutil import iter_md, title_of  # title_of re-exported for back-compat

try:
    from . import index as _index  # SQLite FTS5 + RRF (optional accelerator)
except Exception:  # pragma: no cover - index is an optional accelerator
    _index = None

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STATUS_RE = re.compile(r'^status:\s*"?([^"\n]+?)"?\s*$', re.MULTILINE)


def status_of(text):
    """Frontmatter `status` (lowercased) or '' — only looks at the leading block."""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    block = text[:end] if end != -1 else text
    m = _STATUS_RE.search(block)
    return m.group(1).strip().lower() if m else ""


def normalize(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def tokenize(text):
    return _TOKEN_RE.findall(normalize(text))


def snippet(text, query_terms, width=160):
    flat = " ".join(text.split())
    low = normalize(flat)
    for term in query_terms:
        i = low.find(term)
        if i >= 0:
            start = max(0, i - width // 3)
            return ("…" if start else "") + flat[start:start + width].strip() + "…"
    return flat[:width].strip() + ("…" if len(flat) > width else "")


def collect(cfg, dirs):
    """Read every .md under each search dir; returns ``[(repo_rel_path, text)]``."""
    docs = []
    repo_root = str(cfg.repo_root)
    for d in dirs:
        for path in iter_md(cfg.vault_root / d):
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            docs.append((os.path.relpath(path, repo_root).replace(os.sep, "/"), text))
    return docs


def bm25(docs, query_terms, k1=1.5, b=0.75):
    """Classic BM25 over the doc bodies. Returns list of (rel_path, score, text)."""
    tokenized = [(rel, text, tokenize(text)) for rel, text in docs]
    n = len(tokenized)
    if n == 0:
        return []
    avg_len = sum(len(toks) for _, _, toks in tokenized) / n
    df = {}
    for _, _, toks in tokenized:
        for term in set(toks):
            df[term] = df.get(term, 0) + 1

    scored = []
    for rel, text, toks in tokenized:
        if not toks:
            continue
        tf = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        for term in query_terms:
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            freq = tf[term]
            score += idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * len(toks) / avg_len))
        if score > 0:
            scored.append((rel, score, text))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def _use_index(no_index):
    """True when the FTS5 index path is viable and not opted out."""
    if no_index or _index is None:
        return False
    return _index.index_enabled() and _index.fts5_available()


def _index_results(cfg, query, top, dirs, rrf):
    """Run the indexed (FTS5 + optional RRF) path; returns (rel, score, text) list."""
    hits = _index.search(query, cfg=cfg, top=top, dirs=dirs, rrf=rrf)
    repo_root = str(cfg.repo_root)
    out = []
    for rel, score in hits:
        try:
            with open(os.path.join(repo_root, rel), "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""
        out.append((rel, score, text))
    return out


def run_search(query, cfg=None, top=8, dirs=None, all_statuses=False,
               no_index=False, no_rrf=False):
    """Core search returning ``([(rel, score, text)], hidden_count)``.

    Hidden notes are those with a terminal/dead-history status (configurable),
    excluded unless ``all_statuses`` is True.
    """
    cfg = cfg or _config.load_config()
    query_terms = tokenize(query)
    if not query_terms:
        return [], 0

    # Over-fetch when filtering terminal notes, so the cap still yields ~top live hits.
    fetch_top = top if all_statuses else top * 4
    results = None
    if _use_index(no_index):
        try:
            results = _index_results(cfg, query, fetch_top, dirs, not no_rrf)
        except Exception:  # pragma: no cover - any index hiccup → safe fallback
            results = None
    if results is None:
        docs = collect(cfg, dirs or cfg.search_dirs)
        results = bm25(docs, query_terms)

    # The knowledge index is a navigation hub; RRF over-ranks it (it links
    # everything), so never return it as a search hit.
    idx_rel = (cfg.knowledge_dir / "index.md").relative_to(cfg.repo_root).as_posix()
    results = [r for r in results if r[0].replace(os.sep, "/") != idx_rel]

    hidden = 0
    if not all_statuses:
        hide = cfg.search_hidden_statuses
        kept = [r for r in results if status_of(r[2]) not in hide]
        hidden = len(results) - len(kept)
        results = kept
    return results[:top], hidden


def main(argv=None):
    cfg = _config.load_config()
    ap = argparse.ArgumentParser(
        description="Search the vault (FTS5+RRF if available, pure BM25 fallback).")
    ap.add_argument("query", help="search terms")
    ap.add_argument("--top", type=int, default=8, help="max results (default 8)")
    ap.add_argument("--dir", action="append", help="restrict to a vault subdir (repeatable)")
    ap.add_argument("--no-index", action="store_true", help="force pure BM25 (ignore FTS5 index)")
    ap.add_argument("--no-rrf", action="store_true", help="index without graph fusion (FTS5 only)")
    ap.add_argument("--all", action="store_true",
                    help="include terminal-status notes (closed/implemented/...); default: live only")
    args = ap.parse_args(argv)

    if not tokenize(args.query):
        print("empty query after tokenization", file=sys.stderr)
        return 2

    query_terms = tokenize(args.query)
    results, hidden = run_search(
        args.query, cfg=cfg, top=args.top, dirs=args.dir,
        all_statuses=args.all, no_index=args.no_index, no_rrf=args.no_rrf,
    )

    if not results:
        extra = f" ({hidden} hidden by terminal status — use --all)" if hidden else ""
        print("no results." + extra)
        return 0

    for rel, score, text in results:
        print(f"\n[{score:.2f}] {title_of(text, os.path.basename(rel))}")
        print(f"      {rel}")
        print(f"      {snippet(text, query_terms)}")
    if hidden:
        print(f"\n({hidden} result(s) with terminal status hidden — use --all to include history)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
