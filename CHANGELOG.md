# Changelog

All notable changes to hipocampo are documented here. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims for
[Semantic Versioning](https://semver.org/). For the full design history and phase
status, see [`PLAN.md`](PLAN.md).

## [Unreleased]

### Added
- **`/reflect` skill + `[reflection]` config (Phase 13, opt-in).** A bounded
  in-session generate→critique→revise loop with explicit stopping criteria
  (max-iteration cap, LLM-as-judge score threshold, convergence/no-improvement
  window), seeded from past lessons via `recall` and closed by capturing the
  distilled lesson via `capture` (Reflexion-with-memory). The loop and all judging
  live in the skill — `hipocampo/reflection.py` is deterministic (no LLM calls),
  evaluating the stop predicate from config (mirrors `gate.py`). OFF by default;
  absent/disabled ⇒ a single critique pass, never an unbounded loop.
- **Release automation (`hipocampo/release.py` + `release.yml`).** `prepare` bumps
  the single-sourced version (`.claude-plugin/plugin.json`), promotes
  `## [Unreleased]` → the new version, and refreshes both README status lines
  (version + derived test count); pushing the resulting `v*` tag publishes a GitHub
  Release whose notes are that CHANGELOG section (runner `gh`, no third-party
  Action). A CI `release check` step fails on version drift across
  plugin.json / CHANGELOG / READMEs — the drift that had left `README.pt-BR.md`
  a full minor version behind (now realigned).

### Fixed
- **Capture-sweep ran every turn instead of once at session end (Claude Code).**
  The plugin wired `capture_sweep` to the `Stop` event, which fires after *every*
  assistant turn — so the session-end consolidation sweep (transcript scan, inbox
  decay, stderr report) re-ran mid-session, surfacing as the session "ending" and
  then coming back. Moved it to `SessionEnd` (fires once at true session end, and
  receives `transcript_path`), matching what the Gemini template already did. The
  `stop_hook_active` guard stays for the Codex `Stop` wiring; the `reason=="clear"`
  guard now also covers Claude's `/clear` SessionEnd. Added a regression test
  pinning the plugin's events to `{SessionStart, SessionEnd}`.

## [0.10.0] — 2026-06-18

Engineering cleanup closing the minor backlog (items 5–8) from the 2026-06
quality analysis, plus a Stop-hook crash fix. Backward compatible; `project_mode`/
`team` add config keys that already existed in the example file.

### Added
- `hipocampo/mdutil.py` — one home for the markdown title extractor and the
  `.md` walker that `search`, `index`, and the capture-sweep hook had each
  reimplemented. `search.title_of` and `index.extract_title` are kept as
  re-exports (no API break).
- `project_mode` / `team` are now first-class config keys (defaults `"existing"`
  / `false`) with validation — they were documented in `brain.config.example.toml`
  but missing from `config.py:DEFAULTS` (the exact schema↔code drift the kit
  exists to prevent).
- Stdlib `trace`-based coverage report (`python -m hipocampo.tests.coverage_report`,
  `--fail-under N`) wired as an informational CI job. Zero-dependency.
- Tests for the previously uncovered modules: `frontmatter`, `preflight`,
  `canary`, plus `mdutil` and a config-driven generated-dir view test
  (145 → 182 tests).

### Changed
- `views.py` reads the generated-mirrors directory name from `[dirs] generated`
  instead of a hardcoded `"_generated"` literal.

### Fixed
- **Stop-hook crash on nested `tool_result` content (#7).** `_content_text`
  appended a nested list straight into `" ".join(...)` when a content block's own
  `content` was itself a list (e.g. a Claude `tool_result` whose `content` is a
  list of blocks) → `TypeError: sequence item 0: expected str instance, list
  found` on every Stop-hook run in tool-using sessions. Made `_content_text`
  recursive (flattens str / dict / list at any depth); added a regression case to
  `test_content_text_flattens_shapes`.

## [0.9.1]

Bug-fix release from a full quality audit (code + plugin). All four fixes are
backward compatible; no config or API changes.

### Fixed
- **SessionStart hook crash.** `hooks/ensure_githooks` was missing `import os`,
  so it raised `NameError` on every invocation. Wrapped with `2>/dev/null; exit 0`
  in `hooks.json`, the session never broke — but `core.hooksPath` was never set, so
  the doc-sync gate silently never ran in fresh/ephemeral containers (exactly the
  failure mode the hook exists to prevent). Added `EnsureGithooksTest` (the module
  had zero coverage — root cause of the crash shipping).
- **View path corruption.** `views.load_notes` used a blanket `replace(".", "")`
  that mangled any note path with a dotted directory name (`insights/v1.2/` →
  `v12`); only the top-level `.` now maps to `""`.
- **Secret redaction gaps.** `hooks/capture_sweep.redact` now also scrubs unlabeled
  high-entropy tokens (GitHub PAT, OpenAI `sk-`, Slack `xox*`, JWT) — the labeled
  rule missed credentials pasted without a keyword.
- **Config validation gaps.** `config._validate` now type-checks `areas`,
  `statuses`, `active_states`, `inactive_statuses`, `search.dirs`, `language`, and
  `dirs`, so a bare-string TOML slip fails fast instead of being iterated
  character-by-character downstream.

### Docs
- Added `docs/quality-analysis-2026-06.md` — the full quality audit + a
  competitive/market comparison (mid-May to mid-June 2026).

## [0.9.0]

Two new opt-in capabilities (semantic recall + semi-automatic capture), real
cross-agent support, and a configurable doc-sync gate. All backward compatible —
defaults preserve prior behavior; the new tiers are off until you enable them.

### Added
- **Semantic tier (Phase 11, opt-in).** `[semantic]` config + `pyproject.toml`
  extra (`model2vec` + `sqlite-vec`); `hipocampo/semantic.py` lazy backend
  (`available()` gated on config + deps + `enable_load_extension` + a
  `HIPOCAMPO_SEMANTIC` kill switch); `index.search` fuses a local-embedding vector
  ranking into the existing RRF (empty ⇒ unchanged BM25). New `recall` skill (the
  agent-callable read side) + a router cue in `brain-router-init`. Verified
  end-to-end (`SemanticEndToEndTest`, `skipUnless` the extra is present). No
  daemon/server/vector-DB — embeddable, degrades to BM25 everywhere it's absent.
- **Semi-automatic capture (Phase 12).** `[capture.auto] mode` = `inbox` (legacy
  default) | `draft` | `off`. `draft` stages checkbox candidates in the disposable
  `.brain-cache/pending-capture.md` (never the vault) with a per-session
  `transcript:` pointer; the SessionStart briefing surfaces them; `/capture
  --review` reads the real session and drafts proper notes for one-pass human
  approval. Keeps the human write-gate.
- **Cross-agent support (Codex + Gemini).** Native session-hook wiring
  (`templates/hooks/{codex,gemini}/`), JSON `additionalContext` envelope
  (`session_start --format json`), transcript-shape handling in `capture_sweep`,
  config-driven persona path.
- `brain-scripts-init` now offers to install the semantic extra on opt-in (and
  verify it), and recommends `draft` capture for new setups.
- The kit dogfoods its own memory: `brain.config.toml` + a scaffolded
  `docs/brain/` vault with this release's decisions captured.

### Changed
- **Configurable enforcement (Phase 10).** The doc-sync gate is now per-point
  policy via `[enforcement]` (`pre_commit`/`pre_push`/`ci`, each
  `block`|`warn`|`off`); `hipocampo/gate.py` is the single policy point the git
  hooks + CI call. Defaults `block` everywhere (backward compatible).
- README / README.pt-BR status line and skill count (20 → 21, the new `recall`).

### Fixed
- `validate-doc-links` ignores `<...>` placeholder links in skill/templates
  (angle brackets can't appear in a real path) — removes a false positive.
- `brain.config.example.toml` could not be loaded when copied to
  `brain.config.toml`: TOML absorbed bare keys (`areas`, `validators`,
  `doc_sync_escape_globs`, …) into the preceding `[table]`. Reordered so all bare
  keys precede the first table, with a guard test that loads the shipped example.
- Capture-sweep hook points users at `/capture`, not the removed `/registra`.

## [0.8.3]

### Fixed
- `tests/test_hooks.py`: pin `commit.gpgsign=false` in the temp-repo fixtures so
  the SessionStart tests pass in environments that enforce commit signing.

### Changed
- `version` is now single-sourced in `.claude-plugin/plugin.json`; removed the
  duplicate from `marketplace.json` (plugin.json wins silently, masking drift).
- README / README.pt-BR status line now tracks the real plugin version.
- `docs/ARCHITECTURE.md` lists the actual skill set (16 workflow skills; the data
  flow uses `capture`/`search`, the real skill names).
- `PLAN.md`: corrected the `vault_tools.py` port row and Phase 6 status.

### Added
- `$schema` on both `plugin.json` and `marketplace.json` (editor + CI validation).
- `marketplace.json` plugin entry now mirrors `license`/`homepage`/`repository`.
- CI: Python `3.11`/`3.12`/`3.13` matrix and a manifest-validation job (JSON parse,
  `source: "."`, version single-sourced).
- `config.load_config` fails fast when a `[[doc_sync]]` rule's `paths`/`docs` is a
  bare string instead of a list (a silent char-by-char match footgun).
- `CHANGELOG.md` (this file).

## [0.8.2]

### Fixed
- Plugin SessionStart/Stop hooks can no longer fail or hang the boot: commands end
  with `; exit 0`, and `session_start` no longer blocks reading stdin.

## [0.8.1]

### Fixed
- Plugin hook commands resolve the `hipocampo` package via
  `PYTHONPATH="${CLAUDE_PLUGIN_ROOT:-.}"` so they work regardless of the process
  cwd (previously broke when the plugin ran from outside the repo root).

## [0.8.0] and earlier

See [`PLAN.md`](PLAN.md) for the phase-by-phase history (foundation, retrieval,
governance, generator/workflow skills, bilingual templates, and the
consumer-feedback ports).
