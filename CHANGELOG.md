# Changelog

All notable changes to hipocampo are documented here. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims for
[Semantic Versioning](https://semver.org/). For the full design history and phase
status, see [`PLAN.md`](PLAN.md).

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
