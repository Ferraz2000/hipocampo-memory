# Contribuindo com o hipocampo

🌐 **Português** · [English](CONTRIBUTING.md)

Valeu por ajudar. O kit é pequeno e opinativo de propósito — leia os
não-negociáveis antes de abrir PR.

## Não-negociáveis (enforçados por review + CI)

- **Zero dependências de runtime.** Só biblioteca padrão — TOML via `tomllib`
  (Python 3.11+). Sem PyYAML, sem pip install. Inegociável: o kit precisa rodar
  em qualquer container/CI.
- **Nada específico de projeto hardcoded.** Paths, vocabulários, regras de
  doc-sync, janelas de decay, gatilhos de captura, idioma — tudo vem do
  `brain.config.toml` via `hipocampo.config.load_config()`. Uma string literal
  tipo `"docs/obsidian"` ou nome de capacidade é bug; pertence à config.
- **Markdown é a fonte de verdade.** Qualquer índice/cache (`.brain-cache/`) é
  derivado e descartável; nunca o torne autoritativo.
- **Mantenha o `PLAN.md` honesto.** Terminou de portar/adicionar algo, vire a
  linha correspondente — não declare pronto o que não está.

## Setup de dev

Sem install — só stdlib. Python 3.11+ (CI roda 3.11).

```sh
python -m unittest discover -s hipocampo/tests -v
```

Todos os testes devem passar. Comportamento novo exige teste.

## Layout

Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) pro comportamento. Internals do kit:

```
hipocampo/                 # the python package (zero-dep, stdlib only)
  config.py                # loads brain.config.toml + defaults
  frontmatter.py / vault.py / globs.py
  search.py / index.py     # BM25 + optional FTS5/RRF
  views.py                 # dataview DQL -> static markdown mirrors
  normalize.py / canary.py / inbox_decay.py / preflight.py
  validators/              # doc_links, feature_doc_sync, vault_sync,
                           # views_fresh, router_lint, catalog_sync
  hooks/                   # session_start, capture_sweep, ensure_githooks
  tests/                   # stdlib unittest
plugin/                    # Claude Code plugin (20 skills + hooks.json)
templates/                 # scaffolded into target repos (vault/{en,pt-BR},
                           # githooks, ci, gitignore)
brain.config.example.toml  # documented config schema
```


## Adicionando uma skill

Skill = `plugin/skills/<nome>/SKILL.md` com frontmatter `name` + `description` e
corpo enxuto e operacional (progressive disclosure — aponte pra
`brain.config.toml`/templates em vez de inlinear tudo). Nomes canônicos em **inglês** —
padrão único; frases pt-BR vivem nas descriptions como gatilhos. O `test_skills.py` valida frontmatter de toda skill; adicione o
nome ao set esperado.

## Adicionando um validator

Validator = `hipocampo/validators/<nome>.py` expondo `main(argv=None) -> int`
(0 = passa), funcionando standalone e via `preflight`. Adicione `"<nome>"` ao
default de `validators` (ou documente como opt-in). Escreva teste.

## PRs

- Branch a partir de `main`; PRs miram `main`.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`).
- CI (suite unittest) precisa estar verde.
- Não pule git hooks (`--no-verify`) sem dizer por quê.
