# Log — append-only

Chronological record of ingests and durable decisions (Karpathy LLM-wiki). One
line per event, newest at the top. Cheap to append, never rewritten — it's the
"what happened when" companion to the curated `knowledge/` pages.

Format: `## [YYYY-MM-DD] <kind> | <title>` then an optional one-line note with
links.

<!-- Example:
## [2026-06-12] ingest | Research on agent memory frameworks
Filed raw/sources/2026-06-12-....md; touched knowledge/meta/....md.
-->

## [2026-06-17] capture | Semantic search ships as an opt-in tier
Filed knowledge/architecture/semantic-search-tier.md from raw/sources/2026-06-17-agent-memory-landscape.md.

## [2026-06-17] capture | Semi-automatic capture (draft mode, human-gated)
Filed knowledge/architecture/semi-automatic-capture.md from the same source.

## [2026-06-17] ingest | Agent-memory landscape & embeddable semantic search (2026)
Filed raw/sources/2026-06-17-agent-memory-landscape.md (session research digest).
