---
name: capture
description: Capture the current conversation into durable, git-versioned memory (source / concept / contract / proposal / persona) with a human write-gate. Use when the user says "/capture", "capture this", "save to the brain", or pt-BR phrases like "registra isso" / "salva no brain", "remember this decision", accepts a proactive capture offer, or runs "/capture --review" to triage staged draft candidates.
---

# capture — capture chat into durable knowledge

Implements the capture protocol (`<vault>/capture.md`). Triggered by the explicit
verb or by the user accepting a proactive offer. The human curates by talking; you
do the bookkeeping.

## `--review` — triage draft-mode candidates (agent-reasoned)

When invoked as `/capture --review` (semi-automatic capture, `capture.auto.mode =
draft`): read the staging file `<cache>/pending-capture.md` (cache dir from
`[dirs] cache`, default `.brain-cache/`). It holds, per session, regex-detected
**signals** and a `> transcript: <path>` pointer — **disposable, not yet in the
vault**.

Don't just file the raw snippets — **reason over the session** (proactive
extraction, not verbatim regex hits):

1. **Get context.** If the `transcript` path still exists, read it for the full
   session; otherwise work from the staged snippets + the current conversation.
2. **Draft proper candidates** — for each genuinely durable item, a real title +
   one-line hook + the actual decision/lesson, deduped. Drop noise the regex
   over-captured; add anything worth keeping the regex missed.
3. **Present them together** and let the human accept / edit / drop each in one
   pass (the write-gate is theirs — don't ask file-by-file).
4. **File accepted ones** via the normal capture flow below (classify → file →
   index → log).
5. When done, **delete `pending-capture.md`** (disposable staging, not memory).

Review while the session is fresh so the transcript is still available. If the
staging file is absent, say so — nothing to review.

## Task

Capture what the user marked (or `$ARGUMENTS`):

1. **Classify** into one type, via the boundary heuristic — *would changing this
   require touching code or break a test?*:
   - **Source** (external article/link discussed) → first create
     `<vault>/raw/sources/<YYYY-MM-DD>-<slug>.md` (immutable) from
     `templates/template-source.md`.
   - **Concept/decision** → `<vault>/knowledge/<area>/<slug>.md` from
     `templates/template-knowledge.md`.
   - **Contract** (touches code/tests) → the official doc/skill, **and** treat it as
     a doc-sync change (the `feature_doc_sync` gate applies).
   - **Proposal** → `<vault>/insights/<area>/<slug>.md` from `template-insight.md`.
   - **Persona/preference** (how to work with the user, not a project fact) →
     append to the persona file (`[memory] persona_file` in `brain.config.toml`,
     default `.claude/rules/USER.md`; compact; perishable claims carry `[as of YYYY-MM]`).
2. **Cite the source** in `sources:` (path to `raw/` or a URL); set `provenance`
   (`extracted` | `inferred` | `ambiguous`).
3. **If you wrote to `knowledge/<area>/`**, add a one-line entry under that area in
   `<vault>/knowledge/index.md` (the `vault_sync` validator FAILs a page without an
   index entry). The shipped index has example `## <area>` headers **inside an HTML
   comment** — those don't count. Create a live `## <area>` section (uncomment or
   add one) and put the entry there. Format: `- [<slug>](<area>/<slug>.md) — one-line
   hook. Sources: <...>`.
4. **Append to `<vault>/log.md`** a one-line dated entry, format:
   `## [YYYY-MM-DD] capture | <title>`.
5. **Report in one line** what you wrote and where.

Valid `area` values come from `brain.config.toml` (`areas`). A new area → confirm
with the user first.

## Rules

- **No secrets:** never write tokens, connection strings, credentials, or PII —
  redact before writing.
- The write-gate is the verb/acceptance, not each file — don't ask file-by-file.
- `raw/sources/` is append-only: never rewrite an existing source.
