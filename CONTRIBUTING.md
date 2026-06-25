# Contributing to hipocampo

🌐 [Português](CONTRIBUTING.pt-BR.md) · **English**

Thanks for helping. The kit is small and opinionated on purpose — please read the
non-negotiables before opening a PR.

## Non-negotiables (enforced by review + CI)

- **Zero runtime dependencies.** Standard library only — TOML via `tomllib`
  (Python 3.11+). No PyYAML, no pip installs. The kit must run in any container/CI.
- **Nothing project-specific is hardcoded.** Paths, vocabulary, doc-sync rules,
  decay windows, capture triggers, language — all come from `brain.config.toml`
  via `hipocampo.config.load_config()`. A string literal like `"docs/obsidian"` or
  a capability name is a bug; it belongs in config.
- **Markdown is the source of truth.** Any index/cache (`.brain-cache/`) is derived
  and disposable; never make it authoritative.
- **Keep `PLAN.md` honest.** When you finish porting/adding something, flip its row
  and don't claim done what isn't.

## Dev setup

No install needed — stdlib only. Python 3.11+ (CI runs 3.11; development here uses
3.14).

```sh
python -m unittest discover -s hipocampo/tests -v
```

All tests must pass. New behavior needs a test.

## Layout

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for behavior. Kit internals:

```
hipocampo/                 # the python package (zero-dep, stdlib only)
  config.py                # loads brain.config.toml + defaults
  frontmatter.py / vault.py / globs.py
  search.py / index.py     # BM25 + optional FTS5/RRF
  views.py                 # dataview DQL -> static markdown mirrors
  normalize.py / canary.py / inbox_decay.py / preflight.py
  gate.py                  # enforcement layer (block/warn/off) the hooks+CI call
  validators/              # doc_links, feature_doc_sync, vault_sync,
                           # views_fresh, router_lint, catalog_sync
  hooks/                   # session_start, capture_sweep, ensure_githooks
  tests/                   # stdlib unittest
plugin/                    # Claude Code plugin (20 skills + hooks.json)
templates/                 # scaffolded into target repos (vault/{en,pt-BR},
                           # githooks, ci, gitignore)
brain.config.example.toml  # documented config schema
```


## Adding a skill

A skill is `plugin/skills/<name>/SKILL.md` with `name` + `description`
frontmatter and a lean, operational body (progressive disclosure — point at
`brain.config.toml`/templates rather than inlining everything). Canonical skill names are **English**
(single standard; pt-BR phrases live in skill descriptions as triggers). `test_skills.py`
checks every skill has the required frontmatter; add the name to its expected set.

## Adding a validator

A validator is `hipocampo/validators/<name>.py` exposing `main(argv=None) -> int`
(0 = pass) so it works standalone and via `preflight`. Add `"<name>"` to the
`validators` default (or document it as opt-in). Write a test.

## PRs

- Branch off `main`; PRs target `main`.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`).
- CI (the unittest suite) must be green.
- Don't bypass git hooks (`--no-verify`) without saying why.

## Releasing

The version is single-sourced in `.claude-plugin/plugin.json`; the CHANGELOG and
the README status lines are kept in lockstep by `hipocampo/release.py`. Cutting a
release is one command plus a push:

```sh
python -m hipocampo.release prepare 0.11.0 --tag   # or --minor / --patch
git push --follow-tags
```

`prepare` bumps `plugin.json`, promotes `## [Unreleased]` → `## [0.11.0] — <today>`
(re-opening an empty `[Unreleased]`), refreshes both README status lines (version
+ test count), and tags `v0.11.0`. Pushing the tag triggers
`.github/workflows/release.yml`, which runs the suite and publishes a GitHub
Release whose notes are that version's CHANGELOG section.

`python -m hipocampo.release check` (run in CI) fails on version drift across
plugin.json / CHANGELOG / READMEs — so a hand-edit can't silently desync them.
Keep curating the `## [Unreleased]` section as you land PRs; that prose becomes
the release notes verbatim.
