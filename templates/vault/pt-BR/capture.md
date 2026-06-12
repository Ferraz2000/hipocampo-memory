---
title: Captura — como o chat vira conhecimento durável
type: protocol
area: meta
status: active
tags: [captura, second-brain, agents, protocol]
created: {{DATE}}
updated: {{DATE}}
---

# Captura — como o chat vira conhecimento durável

Protocolo de captura do segundo cérebro. Define como uma **conversa no chat** vira
nota durável **sem o humano editar arquivo**: o humano cura conversando, o agente
faz o *bookkeeping*. É o padrão "LLM wiki" (Karpathy) adaptado a este repo.

> Docs auxiliares: [README](README.md), [context-budget](context-budget.md)
> (disciplina de leitura/escrita), e o `AGENTS.md` raiz (regras globais).

## Decisão de arquitetura

- **Modelo: híbrido por tipo.** A fonte da verdade é dividida pela *natureza* do
  conhecimento (tabela abaixo) — não é "wiki única" nem "tudo promovido".
- **Gatilho: verbo explícito + agente proativo (nível `equilibrado`).**
- **Write-gate humano.** O agente nunca grava sozinho sem um "ok" — seja o verbo
  explícito, seja você aceitando a proposta proativa.

## Os 4 tipos (onde a nota pousa)

| Tipo | Destino | É verdade? | Exemplo |
|---|---|---|---|
| **Fonte** | `raw/sources/` (imutável) | é o lastro | artigo, transcrição, paper, link discutido |
| **Conceito/decisão** | `knowledge/<area>/` | **sim — verdade no brain** | "como pensamos onboarding", "por que adiamos X" |
| **Contrato de código** | docs oficiais (`docs/...`) + skills | sim (gated) | contratos de API, persistência, runtime |
| **Proposta** | `insights/<area>/` (com score) | ainda não | "deveríamos fazer X?" (impact/effort/risk) |

Distinção que falta perceber: "isto é verdade" ≠ "deveríamos fazer isto".
`knowledge/` guarda verdade conceitual; `insights/` guarda proposta com score.

## Heurística de fronteira (contrato vs conceito)

> **Mudar esse conhecimento exigiria tocar código ou quebraria um teste?**
> **Sim → contrato** (camada gated; dispara o gate de doc-sync).
> **Não → conceito** (verdade no brain; vai pra `knowledge/`).

Caso de borda (é os dois — ex.: decisão arquitetural com contrato): grave o
contrato no doc oficial **e** uma página `knowledge/` com o "porquê", linkando
uma na outra.

## 5º destino — persona/preferência (`.claude/rules/USER.md`)

Eixo diferente dos 4 tipos: eles são sobre **o projeto**; este é sobre **como
trabalhar com o usuário**. Heurística:

> **Isto é uma preferência/pet-peeve/convenção pessoal de COMO trabalhar comigo
> (não um fato do projeto)?** → `.claude/rules/USER.md`.

Mecanismo nativo do Claude Code: `.claude/rules/*.md` é **commitado** (sobrevive
ao container web/efêmero) e **auto-carregado toda sessão**; agentes pull-based
(Codex/Gemini) leem via ponteiro no `AGENTS.md`. Mesmo write-gate humano dos
outros destinos; mantenha o arquivo compacto. **Não confundir:** fato que toca
código/teste é contrato (gated), não persona.

## Gatilho 1 — verbo explícito

Dispara o fluxo de captura quando o humano diz, no chat:
- `/capture <o quê>` (slash command), ou
- frases naturais: **"registra isso"**, **"salva no brain"**, "guarda essa decisão".

## Gatilho 2 — agente proativo (nível: equilibrado)

O agente **propõe** registrar (não grava) quando detecta, na conversa:
- uma **decisão durável** ("vamos fazer assim", "decidimos não");
- um **aprendizado/gotcha** reutilizável ("o problema era X");
- uma **fonte externa** trazida e discutida (link/artigo) → propõe ingerir como `source`;
- uma boa **síntese/resposta** que valeria como referência futura → propõe registrar como `knowledge` (*query-filed-back*: a boa resposta vira página);
- uma **preferência/persona** durável ("prefiro", "agora sempre", "me incomoda quando", "não me faça repetir") → propõe registrar em `.claude/rules/USER.md`.

(Níveis: `conservador` = só decisões/contratos; `equilibrado` = + aprendizados e
fontes; `agressivo` = + qualquer conceito/definição novo. Padrão: **equilibrado**.)

### Guardrails anti-nag

- Só propõe se: (a) é durável — importaria numa sessão futura, (b) não está já
  capturado, (c) tem destino claro num dos tipos.
- Pergunta **uma vez, num limite natural** (fim de um raciocínio/tarefa), **nunca
  a cada mensagem**; **agrupa** vários itens numa pergunta só.
- Proposta enxuta: *"isso parece [conceito/fonte/contrato] — registro em
  [destino]?"*. Recusar é barato; **não re-perguntar o mesmo item** na sessão.
- Em tarefa de código focada ou `/low-token`, fica **quieto** — exceto se for
  **contrato** (vale avisar, pois toca o layer gated).

## Fluxo de captura (o que o agente faz)

1. **Classifica** o conteúdo num dos tipos (aplicando a heurística de fronteira).
2. Se há **fonte externa** → cria primeiro `raw/sources/<YYYY-MM-DD>-<slug>.md`
   (imutável) com `templates/template-source.md`.
3. **Escreve no destino**: `knowledge/<area>/<slug>.md` com
   `templates/template-knowledge.md`, ou o doc oficial/skill se for contrato.
4. **Cita a fonte**: campo `sources:` apontando pro `raw/` ou URL — toda afirmação
   rastreia a uma origem (anti-model-collapse).
5. **Atualiza o índice**: adiciona 1 linha em `knowledge/index.md` na área.
6. **Reporta em 1 linha** o que gravou e onde. Não pede permissão arquivo-a-arquivo.

> **Sem segredos (filtro de ingest):** nunca capture tokens, connection strings,
> credenciais ou dados pessoais (PII). Conteúdo colado do chat (logs, configs,
> transcrições) é redigido/omitido antes de gravar — vale para `raw/sources/` e
> `knowledge/`.

## Verificação, busca e staleness

O conhecimento capturado é mantido por três trilhos (operações "Lint/Query" do
padrão LLM-wiki):

- **Lint estrutural (automático):** o validator `vault_sync` (no preflight/CI)
  acusa proveniência quebrada (`sources:` inexistente → FAIL), página `knowledge/`
  velha (> `stale_days` configurado → WARN) e fonte órfã em `raw/sources/` (WARN).
- **Busca (Query):** `python -m hipocampo.search "<termos>"` ranqueia `knowledge/`,
  `insights/`, `specs/` e `raw/sources/`. Caminho rápido: índice SQLite FTS5
  (incremental, com fusão RRF por grafo); fallback automático pro BM25 stdlib.

**Marcador de staleness:** afirmações perecíveis carregam um sufixo `[em AAAA-MM]`
no corpo (ex.: "usamos Postgres gerenciado *[em 2026-05]*") para uma revisão
futura saber o que reconferir.

## Imutabilidade do `raw/`

`raw/sources/` é **somente-anexar**: o agente lê, cita e nunca reescreve. É a
linha de base de verificação contra "model collapse". Correções de entendimento
vão pra página `knowledge/`, não pra fonte.
