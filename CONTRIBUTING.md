# Contributing to hipocampo

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

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). In short: `hipocampo/` is the
package, `plugin/skills/*/SKILL.md` are the skills, `templates/` is what gets
scaffolded into target repos.

## Adding a skill

A skill is `plugin/skills/<name>/SKILL.md` with `name` + `description`
frontmatter and a lean, operational body (progressive disclosure — point at
`brain.config.toml`/templates rather than inlining everything). `test_skills.py`
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
