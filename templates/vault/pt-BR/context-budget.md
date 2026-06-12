---
title: Context Budget — como agentes consultam o vault
type: protocol
area: meta
status: active
tags: [agents, protocol, context-budget]
created: {{DATE}}
updated: {{DATE}}
---

# Context Budget — como agentes consultam o vault

Este protocolo define o **orçamento de contexto** que agentes (Claude Code,
Codex, Gemini) devem respeitar ao trabalhar neste repo. Finalidade: manter o
vault útil como segundo cérebro **sem virar fonte automática de gasto de
tokens**. É a resposta empírica ao context rot — desempenho cai conforme a janela
enche, mesmo em tarefas triviais.

> Docs auxiliares: [README](README.md), [capture](capture.md), `AGENTS.md` raiz.

## Princípio

O vault é **cockpit**. Agentes não devem ler arquivos do vault automaticamente.
Quando precisar de contexto, prefira as fontes oficiais (`docs/...`) e os
roteadores raiz.

**Leitura ampla → sub-agent read-only.** Varredura cross-file (discovery,
auditoria, "ler N arquivos e resumir") deve ser delegada a um sub-agent read-only
que devolve um resumo, protegendo o contexto principal (*bounded-context
principle*). Onde não houver sub-agent (ex.: Codex), limitar ao escopo declarado
e descartar o que não entrar no resultado.

> **Exceção sancionada:** um hook de SessionStart pode injetar um resumo
> **derivado de git** (branch da sessão, branches não-mergeados, merges recentes)
> como contexto operacional *bounded*. A fonte é o estado real do repo, então não
> defasa. Nenhum outro carregamento automático do vault é permitido.

## Index-first reads (padrão Karpathy LLM-wiki)

Para trabalho não-trivial que toca uma área coberta por `knowledge/`, leia
`knowledge/index.md` **primeiro** (barato, poucos KB), identifique as páginas
relevantes e carregue **só essas**. Nunca brute-force o `knowledge/` inteiro, e
nunca ignore silenciosamente quando o tópico claramente combina. Tarefas de
código rotineiras seguem skill/doc oficial — o index é entry point, não obrigação
universal.

## Leitura padrão por tarefa

Para feature/bugfix/refactor normal, o agente lê **apenas**:

1. `AGENTS.md` — roteador raiz e regras globais.
2. O doc oficial do subsistema tocado (`docs/...`).
3. A skill da área (`.claude/skills/<skill>/SKILL.md`).
4. Os arquivos de código diretamente afetados.

Tudo fora dessa lista exige gatilho explícito.

> **Exceção (tarefas não-código):** para trabalho conceitual/produto/decisão (não
> tarefa de código), `knowledge/` é leitura **sancionada** — é a camada de verdade
> conceitual do modelo híbrido (ver [capture](capture.md)). Em tarefas de código,
> continue pulando o vault como acima.

## Quando ler o resto do vault

Insights, roadmap, histórico e demais notas só devem ser lidos quando:

1. **O usuário citar explicitamente** o caminho do arquivo no prompt.
2. **O modo discovery for solicitado** ("faça discovery na área Y", "explore o vault").
3. **Um slash command** que ative o vault for invocado (`/spec`, `/implement`,
   `/execute-insight`, `/from-roadmap`).
4. **A tarefa em si é escrever no vault** — atualizar insight, criar nota, ajustar roadmap.

Em qualquer outro caso, o agente **omite** a leitura do vault.

## Modo low-token

Para tarefas pequenas e bem delimitadas, use `/low-token <tarefa>` ou cole no
início do prompt:

```text
Modo: low-token feature mode.
Leia apenas o mínimo necessário.
Não leia todo o vault; sem insights/roadmap sem pedido explícito.
Implemente a menor mudança correta.
```

Low-token reduz leitura a: `AGENTS.md` + subtree relevante, arquivos de código
diretamente afetados, e a skill da área **se já estiver no routing**. Sem
discovery, sem leitura do vault.

## A captura é a única escrita automática sancionada

A única escrita **automática** permitida no vault é a **captura** — o protocolo de
[capture](capture.md), acionado por `/capture` ou uma proposta proativa aceita.
É *bounded* e sempre com write-gate humano. Fora da captura, agentes não escrevem
no vault sem gatilho explícito.

## Critérios de aceite

- Tarefa pequena (typo, refactor de um arquivo, mudança só em testes) **não
  dispara** leitura automática do vault.
- Vault continua acessível ao humano; nenhuma nota é apagada.
- Slash commands permitem usar o vault sob demanda.
