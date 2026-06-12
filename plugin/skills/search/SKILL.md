---
name: search
description: Keyword-search the vault (knowledge/insights/specs/raw sources) by relevance, BM25 with an optional FTS5 fast path. Use when the user says "/search", "search the brain/vault", or the pt-BR alias "/busca", "find notes about X".
---

# search — search the vault

Run the kit's search over the vault and report the ranked hits.

## Task

1. Run: `python3 -m hipocampo.search "<terms>"` (add `--top N`, `--dir <subdir>`, or
   `--all` to include terminal-status notes when the user asks).
2. Present the ranked results: title, path, one-line snippet. Offer to open the top
   hits — don't dump full files (respect the context budget).

## Notes

- It reads everything project-specific (vault root, searched dirs, hidden statuses)
  from `brain.config.toml`. Terminal-status notes (closed/implemented/…) are hidden
  by default; `--all` includes them.
- Fast path is a SQLite FTS5 index with RRF graph fusion; it falls back to pure
  BM25 automatically, so it always runs (headless/CI/local).
