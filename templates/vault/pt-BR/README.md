---
title: Vault — visão geral & convenções
type: index
area: meta
status: active
tags: [vault, second-brain, convencoes]
created: {{DATE}}
updated: {{DATE}}
---

# Vault — visão geral & convenções

Este é o segundo cérebro do projeto: memória durável, versionada em git, com
write-gate humano, para agentes de código. Scaffoldado por
[hipocampo](https://github.com/Ferraz2000/hipocampo-memory).

> **Agentes:** não façam bulk-read deste vault. Sigam
> [context-budget](context-budget.md) (index-first, never bulk-read) e
> [capture](capture.md) (como o chat vira nota durável, com write-gate humano).

## Layout

| Caminho | O quê | É verdade? |
|------|------|--------|
| `knowledge/` | conceitos & decisões duráveis (a wiki) | sim |
| `knowledge/index.md` | entry point index-first (barato) | — |
| `knowledge/_inbox/` | sweeps de auto-captura aguardando triagem | não (efêmero) |
| `insights/` | propostas com score ("deveríamos?") | ainda não |
| `raw/sources/` | fontes ingeridas imutáveis (proveniência) | lastro |
| `specs/` | mini design docs aprovados | sim |
| `adrs/` | architectural decision records | sim |
| `log.md` | log cronológico append-only de ingests/decisões | — |
| `templates/` | templates de nota | — |

## Frontmatter canônico

Frontmatter é **verdade de máquina**. Qualquer dashboard/readout é projeção dele,
nunca hand-curated.

**página knowledge:**
```yaml
---
title: ...
type: knowledge
area: <uma das áreas configuradas>
status: active        # active | superseded
confidence: high      # low | medium | high
provenance: inferred  # extracted | inferred | ambiguous
sources:              # toda afirmação rastreia a uma origem
  - raw/sources/<arquivo>.md   # ou uma URL https
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
---
```

**insight (proposta):** adiciona `impact`/`effort`/`risk`/`confidence`
(low/medium/high) e `next_step`; `status` do conjunto fechado abaixo.

**source:** `type: source`, `source_type`, `url`, `provenance: external`,
`retrieved`.

## Vocabulário fechado de status (insights)

`triage` · `active` · `deferred` · `implemented` · `closed` · `rejected` ·
`superseded` · `promoted`

Para fechar/reabrir/repriorizar, edite **só** o frontmatter do insight. O
validator `vault_sync` enforça o vocabulário fechado e a consistência do índice.

## Regras globais

- **Sem segredos no vault.** Nunca commite tokens, connection strings,
  credenciais ou PII. Redija conteúdo colado do chat antes de capturar.
- **`raw/` é append-only.** Leia e cite, nunca reescreva; correções vão pra
  página `knowledge/`.
- **Index-first.** Uma página `knowledge/` nova/movida ganha 1 linha em
  `knowledge/index.md` na mesma mudança.
