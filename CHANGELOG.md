# Changelog

All notable changes to hipocampo are documented here. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims for
[Semantic Versioning](https://semver.org/). For the full design history and phase
status, see [`PLAN.md`](PLAN.md).

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
