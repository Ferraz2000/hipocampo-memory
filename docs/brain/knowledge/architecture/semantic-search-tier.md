---
title: Semantic search ships as an opt-in tier, not in the core
type: knowledge
area: architecture
status: active
confidence: high
provenance: extracted
sources:
  - raw/sources/2026-06-17-agent-memory-landscape.md
created: 2026-06-17
updated: 2026-06-17
valid_until: ""
superseded_by: ""
tags: [knowledge, architecture, semantic-search, tiers]
---

# Semantic search ships as an opt-in tier, not in the core

> Local-embedding semantic recall is an **opt-in `[semantic]` extra**
> (`model2vec` + `sqlite-vec`), never a core dependency. The core stays
> stdlib-only and runs in any container/CI; enabling the tier fuses a vector
> ranking into the existing RRF, and any missing piece degrades silently to BM25.

## Context

The core's whole value is zero-dependency, auditable, markdown-first memory. The
temptation is to add semantic search the way the market does it (a server + a
vector DB + LLM consolidation). The benchmark says we don't need that: an
embeddable BM25+vector hybrid reaches ~95% vs ~96.6% for a full vector DB — a
server buys ~1.4 points. See `raw/sources/2026-06-17-agent-memory-landscape.md`.

## The decision / concept

- Packaging: `pyproject.toml` declares a `[semantic]` extra. The core has zero
  runtime deps; the tier adds `model2vec` (static CPU embeddings) + `sqlite-vec`
  (in-process SQLite extension) — **no daemon, no server, no external DB**.
- `hipocampo/semantic.py` is lazy: it imports the heavy deps only when
  `available(cfg)` holds (config `enabled` AND deps import AND
  `enable_load_extension`), gated further by a `HIPOCAMPO_SEMANTIC` kill switch.
- `index.search` fuses the vector ranking into the same `rrf_fuse` used for
  FTS5+graph. Empty vector hits ⇒ one code path that degenerates to today's BM25.
- **Why:** maximize recall on fuzzy/paraphrased queries (where BM25 is weakest)
  without breaking "runs anywhere" or the markdown-as-truth invariant — the vec0
  store is a disposable index that rebuilds from the `.md` files.

## Related

- [[semi-automatic-capture]]
