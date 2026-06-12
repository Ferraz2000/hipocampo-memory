---
name: audit
description: Fact-check a vault page against its cited sources — every claim must trace to a source that actually supports it. Use when the user says "/audit <path>", "fact-check this note", "fact-check this note", "verify this page against its sources".
---

# audit — fact-check a page against its sources

The anti-model-collapse audit: `knowledge/` is only as good as its provenance.

## Task

`$ARGUMENTS` = path (or slug) of a `knowledge/` or `insights/` page.

1. **Read the page**; extract its factual claims and its `sources:` list.
2. **Load each source**: `raw/sources/` files directly; external URLs fetched if
   tooling allows (else mark UNVERIFIABLE-HERE, don't guess). For several
   independent sources, parallel read-only sub-agents keep the main context lean.
3. **Map claim → source**, verdict each: SUPPORTED (quote/line), PARTIAL
   (supported with caveats the page omits), UNSUPPORTED (no source backs it),
   CONTRADICTED (source says otherwise), STALE (was true; time-sensitive and the
   page lacks `[as of]`/`valid_until`).
4. **Report by severity**: CONTRADICTED first, then UNSUPPORTED, PARTIAL, STALE.
   Quote the exact page sentence and the exact source passage.
5. **Offer fixes** (write-gated): correct the page, add the missing caveat, mark
   `superseded_by`, or set `valid_until`. Apply only what's approved; `raw/` is
   never edited.

## Rules

- Verdicts come from the sources, not from your own knowledge — if you "know"
  the page is right but the source doesn't show it, that's UNSUPPORTED.
- No source list at all → that's the finding; propose adding provenance.
