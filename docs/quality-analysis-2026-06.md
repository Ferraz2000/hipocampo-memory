# Análise de Qualidade — `hipocampo` + Comparativo de Mercado

> **Data:** 2026-06-17 · **Versão analisada:** v0.9.0 · **Janela de pesquisa:** ~15 mai – 17 jun 2026
> **Método:** auditoria de código local (leitura + execução) + pesquisa em 5 frentes
> (GitHub competitivo, Hacker News, YouTube/conferência, blogs/vendor, Reddit-via-agregadores).
> Os bugs marcados *(verificado)* foram reproduzidos executando o código.

---

## 1. Sumário executivo

O **hipocampo é um projeto de qualidade acima da média** para o seu nicho: arquitetura
limpa, *zero-dependency* de verdade (só stdlib), degradação graciosa exemplar, docstrings
excelentes e uma camada de governança (write-gate humano + doc-sync gate) que **nenhum
concorrente direto empacota**. A pesquisa de mercado confirma que ele apostou no padrão
arquitetural *certo*: em mai–jun/2026 o ecossistema convergiu para "markdown é a verdade +
índice descartável" — exatamente a tese dele.

A auditoria encontrou **4 defeitos reais** que contradiziam promessas do README (incluindo
**1 crítico reproduzido**: o hook que roda em toda sessão crashava e nunca cumpria sua
função). **Todos foram corrigidos e testados** — ver §6.

**Nota geral: B+ / 8.0 de 10.** Engenharia forte e posicionamento de mercado certeiro;
os bugs estavam em pontos sem cobertura de teste e minavam justamente os diferenciais
vendidos (governança e redação de segredos).

| Dimensão | Nota | Resumo |
|---|---|---|
| Arquitetura & organização | A− | Camadas limpas, política num lugar só, aceleradores opcionais bem isolados |
| Qualidade do código | B | Ótimas docstrings; alguma duplicação tripla; "nada hardcoded" vaza em 3 pontos |
| Testes | B− → B | 142 testes com asserts reais; buracos em `frontmatter`/`preflight`/`ensure_githooks`; sem medição de coverage |
| Robustez / portabilidade | A | Zero-dep confirmado; fallback FTS5/sqlite-vec/TOML impecável |
| Segurança | C+ → B− | Redator de segredos endurecido (ver §6); write-gate é só protocolar (honestamente documentado) |
| Docs & honestidade | A | `PLAN.md` honesto, ARQUITETURA forte; 1 drift de config |
| Posicionamento de mercado | A | Aposta arquitetural validada pelo ecossistema; governança é lacuna não-ocupada |

---

## 2. Capacidades do projeto (descrição precisa)

O hipocampo **não é só o modo sem dependências**. É um core leve com três camadas de
inteligência opt-in por cima:

1. **Core zero-dep** — markdown como fonte de verdade, BM25/FTS5, doc-sync gate, validators,
   hooks. Só stdlib (`tomllib`, `sqlite3`, …). Roda em qualquer container/CI sem `pip install`.
2. **Tier semântico opt-in** (`hipocampo/semantic.py`, Phase 11) — embeddings locais
   `model2vec` → store `sqlite-vec` (`vec0`), fundidos com BM25 via RRF. **Busca vetorial
   existe**; está off por padrão (precisa `pip install model2vec sqlite-vec` + sqlite com
   `enable_load_extension`). Ausente qualquer um → fallback silencioso para BM25.
3. **Recall automático do agente** (skill `recall`) — o lado *agent-callable* (`LoadMemoryTool`):
   o agente compõe a própria query no meio da tarefa e puxa só o relevante, **sem o usuário
   pedir** ("recall before asking the user about past decisions").
4. **Captura proposta pelo agente** (`capture.auto.mode = "draft"`, Phase 12) — o hook de
   fim-de-sessão (`capture_sweep`) rascunha candidatos e o agente **propõe** salvar; o humano
   só aprova. Substitui o "só `/capture` manual" sem abrir mão do write-gate.

---

## 3. Auditoria de qualidade (código + plugin)

### ✅ Pontos fortes (confirmados)

- **Zero-dependency real.** Todo import em `hipocampo/` é stdlib; `model2vec`/`sqlite_vec`
  carregam *lazy* dentro de `_deps()` com fallback de `ImportError`.
- **Degradação graciosa exemplar.** FTS5 ausente → testa um `CREATE VIRTUAL TABLE` real e cai
  para BM25; sqlite-vec ausente → gate de 3 checagens em `semantic.available()`; erro de TOML
  → `ConfigError` com o caminho do erro. Um único caminho de código serve os dois tiers.
- **Política num lugar só.** `gate.py` (block/warn/off) → `preflight` → validators. Os
  validators sempre reportam a verdade; só o gate decide se bloqueia.
- **Segurança de subprocess.** Nenhum `shell=True` no projeto; git access isolado atrás de
  `_git.py` (nunca levanta). Sem `eval`/`exec`, sem path-traversal.
- **Plugin bem empacotado.** `plugin.json`/`marketplace.json` válidos; `hooks.json` com
  fallback de interpretador (`python3 || python`) e `exit 0` para nunca travar a sessão.
- **Docstrings e honestidade.** Cada módulo explica o *porquê*; `PLAN.md` usa ✅/🟡/⬜ sem inflar.

### 🔴 Achados priorizados (todos corrigidos — ver §6)

**CRÍTICO**

1. **`hooks/ensure_githooks.py` crashava em toda invocação — faltava `import os`.**
   *(verificado: `NameError`, exit 1)*. No `hooks.json` rodava com `2>/dev/null; exit 0`,
   então a sessão não quebrava — mas o hook **nunca configurava `core.hooksPath`**, e o
   doc-sync gate silenciosamente nunca rodava em containers web/efêmeros (o cenário que ele
   existe para resolver). Causa raiz: módulo com **zero testes**.

**MAIOR**

2. **`views.py` corrompia paths com ponto no nome do diretório.** *(verificado:
   `insights/v1.2/foo.md` → `insights/v12`)*. O `replace(".", "")` era cego; a intenção era
   só transformar `.` (raiz) em `""`.

3. **Redator de segredos mais fraco que o anunciado** (`capture_sweep.py`). O regex só
   disparava em `keyword <is|=|:> valor`. Tokens de alta entropia **sem rótulo** (GitHub PAT
   `ghp_…`, OpenAI `sk-…`, Slack `xox*-…`, JWT) vazavam *verbatim* para o inbox versionado.

4. **`config._validate` não checava tipos de `areas`/`statuses`/`dirs`/`search.dirs`/`language`.**
   Um `areas = "meta"` (string) passava e depois era iterado caractere-a-caractere — o modo de
   falha que `_require_str_list` foi escrito para prevenir, mas não aplicado nesses campos.

**MENOR (não corrigidos — backlog)**

5. Lógica de `title`/`_iter_md` triplicada (`search.py`, `index.py`, `capture_sweep.py`).
6. `"_generated"` hardcoded em `views.py` em vez de `dirs.generated` do config.
7. `project_mode`/`team` no `brain.config.example.toml` mas ausentes de `config.py:DEFAULTS`.
8. **Sem medição de coverage** e módulos core sem teste (`frontmatter`, `preflight`, `canary`).
   Os dois bugs verificados viviam justamente no código sem cobertura.

---

## 4. Cenário competitivo

O mercado de "memória de agentes" (mai–jun/2026) se divide em três campos; o hipocampo está no
**menor e mais diferenciado** (markdown+git+governança).

| Projeto | Storage | Deps | Foco coding-agent | Adoção | Diferença-chave vs markdown+git+governança |
|---|---|---|---|---|---|
| **hipocampo** | Markdown + git; índice `.brain-cache/` descartável | **Zero** (stdlib) | Sim (CC/Codex/Gemini) | — | — |
| **Letta Code** (Context Repositories) | Markdown em git local; worktrees | Node/TS, runtime | **Sim, explícito** | 2.7k★, muito ativo | Mais próximo arquiteturalmente, mas **agente auto-gerencia — sem aprovação humana**; não zero-dep |
| **basic-memory** | Markdown + índice SQLite/Postgres | Python, FastEmbed, ORM | Sim (tem plugin CC) | 3.2k★ | Grafo semântico + Obsidian, mas **humano e IA escrevem livremente, sem gate**; AGPL |
| **memsearch** (Zilliz) | Markdown é a verdade; Milvus = cache | Python, Milvus Lite | **Sim** | 2.1k★ | Filosofia "files-are-truth" idêntica + híbrido BM25+denso, mas **auto-captura sem gate** |
| **claude-mem** | SQLite local + FTS5 + Chroma | Node, Chroma | Sim (plugin CC) | trending fev/26 | Auto-captura/compressão/re-injeção, **sem gate, sem governança** |
| **DiffMem** | Markdown + git diffs (sem índice) | git, grep | Sim | nicho | "No vector DB, no embeddings" — ainda mais minimalista; sem busca ranqueada |
| **mem0** | Vector DB (Qdrant) + híbrido | spaCy, LLM, vector store | Sim | **58.7k★** | Maior ecossistema + melhores benchmarks (92.5 LoCoMo), mas **DB, não auditável por git** |
| **Zep/Graphiti** | Grafo temporal (Neo4j) | Neo4j, LLM key | Enterprise | 13k★ | SOTA recall temporal (63.8% LongMemEval) + SOC2/HIPAA, mas **infra pesada** |
| **Anthropic memory tool / CLAUDE.md** | Arquivos `.md`, sem índice | Built-in | Sim | plataforma | Oficial mas **sem busca semântica, sem git, sem governança**, single-vendor |

### Diferencial genuíno (lacuna não-ocupada)

1. **Write-gate humano + doc-sync gate de governança.** *Todo* concorrente próximo deixa o
   **agente** escrever memória autonomamente. O discurso de governança de 2026 (gates de
   aprovação, audit trails, EU AI Act começando em 2-ago-2026) está em blogs e frameworks —
   **não empacotado em nenhum kit de memória.** Esse é o terreno do hipocampo.
2. **Zero dependência — único.** Todo concorrente puxa pelo menos um de: vector DB, lib de
   embedding, ORM, ou runtime Node.
3. **Auditável por git por construção** (diff + revert + review humano).
4. **Cross-agent sem vendor lock-in** — vantagem sobre os primitivos nativos (single-vendor).

### Onde os concorrentes ganham

- **Recall semântico maduro:** mem0 (92.5 LoCoMo) e Zep (SOTA temporal) muito à frente.
- **Adoção/ecossistema:** mem0 (58.7k★), Graphiti (13k★) ofuscam o campo markdown.
- **Compliance enterprise:** Zep entrega SOC2/HIPAA/GDPR — RFP-readiness que o hipocampo não mira.

---

## 5. O que a comunidade quer (últimos 30 dias) × o que o hipocampo entrega

| O que a comunidade pede (mai–jun/2026) | hipocampo entrega? |
|---|---|
| **Markdown/git-nativo, local-first, versionável** ("treat knowledge like source control") — *tese dominante* | ✅ É a tese central |
| **Backlash contra vector-DB** ("80% da qualidade vem de disciplina, 20% de infra") | ✅ Zero-dep, BM25 first, semântica opt-in |
| **Memória estreita e de alto sinal** ("knowing what to forget > remembering more") | ✅ write-gate + decay + capture curado |
| **Curadoria human-in-the-loop / agent-directed** ("confirmation-driven learning") | ✅ Diferencial central — o write-gate humano |
| **Combater doc-rot / staleness** ("stale facts confidently wrong") | ✅ doc-sync gate + `valid_until` + `garden` |
| **CLAUDE.md enxuto** (~100-150 instruções úteis; alvo 80-120 linhas) | ✅ `router_lint` impõe cap de linhas no `AGENTS.md` |
| **Retrieval híbrido** (semântico + BM25 + entidade + temporal) | 🟡 Parcial — BM25/FTS5 + RRF + embeddings opcionais; sem entidade/temporal |
| **Recall semântico de alta precisão em escala** | 🟡 Deliberadamente leve — perde para mem0/Zep |
| **Anti vendor/framework lock-in** | ✅ Cross-agent, sem runtime proprietário |
| **Privacidade / on-device** | ✅ Tudo local, sem API key no core |
| 🆕 **Memory poisoning como superfície de ataque** (tema novo de mai/2026) | ⚠️ Lacuna emergente — o write-gate ajuda (review por diff), mas sem defesa explícita |
| **Servidores MCP de memória** (Hindsight, OpenMemory MCP) | ❌ Não expõe MCP — só skills/hooks. *Mas:* a comunidade reclama do **token-bloat de MCP** ("67k tokens só de conectar 4 servidores"), então o caminho skill/hook de baixo-token é, na verdade, uma vantagem |

**Sinais do Reddit (via agregadores — reddit.com bloqueado para o crawler):** "Claude Code
esquecendo entre sessões" é a queixa #1; filesystem-first vence (AutoGPT removeu vector-DBs e
voltou para JSON); auto-memory nativo (MEMORY.md) incha e duplica → demanda por alternativas
(uma skill da comunidade teria batido 26k downloads na 1ª semana). Tudo isso reforça a tese do
hipocampo.

**Leitura estratégica:** o hipocampo está alinhado a ~9 das ~12 demandas atuais, e seu
diferencial (governança/write-gate) ataca as duas dores mais citadas — *staleness/"confidently
wrong"* e *"curar > capturar"*. Lacunas reais: recall semântico em escala (intencional),
interface MCP, e a fronteira nova de *memory poisoning*.

---

## 6. Correções aplicadas nesta análise

Todas verificadas executando o código; suíte **142 → 145 testes, verde**.

| # | Sev | Arquivo | Fix |
|---|---|---|---|
| 1 | 🔴 Crítico | `hooks/ensure_githooks.py` | Adicionado `import os` — hook não crasha mais; configura `core.hooksPath` |
| 2 | 🟠 Maior | `views.py` | `"" if rel.parent == Path(".") else rel.parent.as_posix()` — preserva dirs com ponto |
| 3 | 🟠 Maior | `hooks/capture_sweep.py` | Padrões de token sem rótulo: GitHub `gh[pousr]_`, OpenAI `sk-`, Slack `xox[baprs]-`, JWT |
| 4 | 🟠 Maior | `config.py` | `_validate` agora type-checa `areas`/`statuses`/`active_states`/`inactive_statuses`/`search.dirs`/`language`/`dirs` |
| — | teste | `tests/test_hooks.py` | `EnsureGithooksTest` (regressão do crash) + asserts de redação de token sem rótulo |

---

## 7. Recomendações (backlog priorizado)

**Posicionamento (o mercado confirma):**

1. Vender **"você controla e revisa o que o agente lembra"** (governança/auditabilidade/trust),
   não recall. É o terreno que ninguém ocupa e a dor #1 da comunidade.
2. Avaliar uma **interface MCP fina e opcional** (Retain/Recall), **preservando** o caminho
   skill/hook de baixo-token como padrão — não substituí-lo (o token-bloat de MCP é uma queixa
   recorrente; o baixo overhead atual é um diferencial a defender).
3. Considerar uma postura explícita sobre **memory poisoning** — o diff-review humano é meio
   caminho andado; seria um diferencial *à frente* do mercado.

**Qualidade de engenharia (itens menores 5–8 da §3):**

4. Consolidar `title`/`_iter_md` num helper único.
5. Ler `dirs.generated` do config em `views.py` em vez do literal `"_generated"`.
6. Reconciliar `project_mode`/`team` entre o exemplo TOML e `config.py:DEFAULTS`.
7. Adicionar medição de coverage (via stdlib `trace`, para manter zero-dep) e fechar os buracos
   em `frontmatter`/`preflight`/`canary`.

---

## Fontes (primárias primeiro)

- **Competidores:** Letta Context Repositories (letta.com/blog/context-repositories), basic-memory
  (github.com/basicmachines-co/basic-memory), memsearch (github.com/zilliztech/memsearch),
  claude-mem, DiffMem (github.com/Growth-Kinetics/DiffMem), mem0 (github.com/mem0ai/mem0),
  Zep/Graphiti (github.com/getzep/graphiti), Anthropic memory tool
  (platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool).
- **Mercado/comunidade:** mem0 "State of AI Agent Memory 2026" (mem0.ai/blog, 16-jun-2026),
  "The Complete Guide to CLAUDE.md" (Medium, 9-mai-2026), "Notes from Code with Claude 2026"
  (chrisebert.net, 8-mai-2026), Hindsight "The Case Against External Vector DBs"
  (hindsight.vectorize.io, 12-mai-2026), "memweave: Zero-Infra Agent Memory" (Towards Data
  Science, 16-abr-2026), HN "Agent Memory: An Anatomy" / "Hippo" / "Agentic Memory Is Still an
  Unsolved Problem", morphllm.com "Claude Code Reddit (2026)", sedim3nt Substack.

> *Caveats:* contagens de estrelas e datas são as reportadas em 17-jun-2026 e podem estar
> levemente defasadas. Threads frescos e extraíveis de Reddit/StackOverflow não foram acessíveis
> na janela (crawler bloqueado para reddit.com); o sentimento do Reddit vem de agregadores
> secundários. Números de benchmark de vendor (mem0/Zep) são auto-reportados.
