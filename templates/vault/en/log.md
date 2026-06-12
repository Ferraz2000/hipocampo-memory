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
