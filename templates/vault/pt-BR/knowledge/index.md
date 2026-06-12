---
title: Knowledge — índice de navegação
type: index
area: meta
status: active
created: {{DATE}}
updated: {{DATE}}
tags: [knowledge, index, navigation]
---

# Knowledge — índice de navegação

> **Entry point barato** (padrão Karpathy LLM-wiki). Lista cada
> `knowledge/<area>/X.md` com 1 linha de what's-it-about + suas fontes. Agentes
> leem ESTE (~poucos KB) → identificam as páginas relevantes → carregam só essas.
> Nunca brute-force o vault inteiro.
>
> Quando ler: a tarefa toca uma das áreas abaixo e não é trivial (decisão
> arquitetural, mudança de gate de fluxo, mudança cross-camada). Tarefas de código
> rotineiras seguem skill/doc oficial — o index é entry point, não obrigação
> universal.
>
> Como manter: atualizado pelo `/registra` quando cria/move página. O validator
> `vault_sync` enforça consistência (página sem entry → FAIL; entry sem arquivo →
> FAIL).

<!--
Áreas e entries aparecem aqui conforme o conhecimento é capturado. 1 linha por página:

## meta
- [alguma-decisao](meta/alguma-decisao.md) — hook de 1 linha. Fontes: raw/sources/<arquivo>.md.

## architecture
- [algum-padrao](architecture/algum-padrao.md) — hook de 1 linha. Fontes: ...
-->
