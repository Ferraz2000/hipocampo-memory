# Log — append-only

Registro cronológico de ingests e decisões duráveis (padrão Karpathy LLM-wiki). 1
linha por evento, mais recente no topo. Barato de anexar, nunca reescrito — é o
companheiro "o que aconteceu quando" das páginas curadas em `knowledge/`.

Formato: `## [AAAA-MM-DD] <tipo> | <título>` e uma linha opcional com links.

<!-- Exemplo:
## [2026-06-12] ingest | Pesquisa de frameworks de memória de agentes
Gravado raw/sources/2026-06-12-....md; tocou knowledge/meta/....md.
-->
