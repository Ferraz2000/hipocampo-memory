---
title: Agent-memory landscape & embeddable semantic search (2026)
type: source
area: architecture
source_type: research
url: ""
provenance: external
status: active
retrieved: 2026-06-17
created: 2026-06-17
updated: 2026-06-17
tags: [source, research, memory, semantic-search]
---

# Agent-memory landscape & embeddable semantic search (2026)

> **Immutable.** Reference capture from the session research that shaped the
> tiered design. The agent reads and cites; corrections go to the `knowledge/`
> pages.

## Metadata

- Origin: web research (mem0/Zep/Letta blogs, sqlite-vec & model2vec docs,
  LongMemEval benchmark write-ups, "memory as a tool" 2026 articles).
- Ingested: 2026-06-17 via chat research.
- knowledge/ pages citing this source: `architecture/semantic-search-tier.md`,
  `architecture/semi-automatic-capture.md`.

## Faithful summary

- The 2026 field (mem0, Zep/Graphiti, Letta/MemGPT, Cognee) converged on
  **markdown/source-of-truth + a derived index**; the heavy players add servers,
  vector DBs, and LLM consolidation that hipocampo deliberately rejects.
- **LongMemEval-S**: BM25 alone ≈ 86%; **BM25+vector hybrid ≈ 95.2%**; pure vector
  DB ≈ 96.6%. So an *embeddable* hybrid captures almost all the gain — a server
  buys ~1.4 pts more. The gain concentrates in fuzzy/paraphrased queries
  (preferences 60% → 83%); exact-term lookups are already strong on BM25.
- **sqlite-vec** + **model2vec** give vector search with **no daemon**: an
  in-process SQLite extension + static CPU embeddings (~30 MB model). This is what
  dissolves the "semantic = server" tension.
- **Retrieval is two surfaces**: a small deterministic preload (briefing) +
  agent-decided recall (a tool the agent calls mid-task). 2026 benchmarks favor
  "memory as a tool" (the agent composes its own query, lower-noise than
  always-inject). Google ADK names them `PreloadMemoryTool` / `LoadMemoryTool`.
- **Proactive memory extraction** (vs. summarize-everything) and **sleep-time
  consolidation** (offline, at session end) back the semi-automatic capture design.

## Key quotes

- "BM25+Vector hybrid achieved 95.2% accuracy, nearly matching pure vector search
  at 96.6%."
- "sqlite-vec removes the operational burden of a separate vector database for
  local, embedded systems."
