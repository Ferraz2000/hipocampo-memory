# hipocampo

🌐 **Português** · [English](README.md)

**Memória persistente, versionada em git e com write-gate humano para agentes de
código.** Um kit reutilizável que scaffolda um vault de conhecimento + skills +
hooks + scripts de validação em **qualquer projeto, qualquer linguagem** — pra
seus agentes (Claude Code, Codex, Gemini) pararem de esquecer entre sessões e de
reaprender as mesmas coisas.

> *Hipocampo* é a região do cérebro que consolida memória de curto prazo em
> longo prazo. É exatamente o que este kit faz: um pipeline com write-gate que
> move um `_inbox/` de capturas cruas pra uma base `knowledge/` curada e
> auditável, que vive no seu repo e se compõe ao longo do tempo.

**Status: v0.6.x — usável.** 94 testes, CI verde, validado ponta-a-ponta cinco
vezes (dogfood mecânico em Go, walkthrough de agente real em Node, auditoria
adversarial independente, re-auditoria pós-fix com CI real + install real do
plugin, e um projeto de produção migrado como primeiro consumidor). Ver
[`PLAN.md`](PLAN.md).

## Quickstart (2 minutos)

```sh
/plugin marketplace add Ferraz2000/hipocampo     # Claude Code (skills + hooks)
/plugin install hipocampo@hipocampo
# ou cross-agent (Claude Code / Codex / Gemini), só as skills:
npx skills add Ferraz2000/hipocampo
```

No seu projeto, você só precisa de **três skills** pra começar:

```
/brain-init             # scaffolda o vault + brain.config.toml
/registra <algo>        # captura uma decisão/lição como nota revisável (alias de /capture)
/busca <termos>         # busca o que o brain já sabe (alias de /search)
```

O resto (geração de router, gates vendorados, ciclo de vida de insights) está lá
pra quando você quiser — veja [a caixa de ferramentas completa](#a-caixa-de-ferramentas-completa).
Não precisa aprender tudo antes.

## Como fica (antes / depois)

**Antes** — o agente muda uma área sensível; o doc apodrece em silêncio:

```sh
$ git commit -m "feat: muda modelo de persistência"
[main abc1234] feat: muda modelo de persistência    # o drift de doc começa aqui
```

**Depois** — o gate de doc-sync (pre-commit → pre-push → CI, mesma regra) bloqueia:

```sh
$ git commit -m "feat: muda modelo de persistência"
feature-doc-sync validation FAILED
  Sensitive area changed without its doc update: persistence
  Files:  src/app/migrations/0042_split.sql
  Update one of: docs/architecture/persistence.md
$ git add docs/architecture/persistence.md && git commit ...   # passa
```

E a memória vira **diff revisável**, não caixa-preta:

```diff
+ docs/brain/knowledge/architecture/error-style.md   # /registra escreveu isto
+ docs/brain/knowledge/index.md                       # +1 linha no índice
+ docs/brain/log.md                                   # +1 linha datada no log
```

Agente propõe → você aprova → cai no git → o `vault_sync` mantém honesto
(proveniência, índice, vocabulário). `python -m hipocampo.canary` prova que os
gates mordem contra a *sua* config (7 cenários adversariais).

## Por que isto e não um framework de memória

O estado da arte 2025–2026 convergiu pra **markdown como fonte de verdade + um
índice derivado opcional** (auto-memory da Anthropic, MemFS do Letta Code,
OpenClaw/memsearch, basic-memory — independentemente). Memória em DB
(mem0/Zep/claude-flow) abre mão da auditabilidade por git-diff. A aposta do
hipocampo é a durável, mais a peça que nenhum framework publicado entrega bem:
**governança** — write-gate humano, frontmatter-como-verdade e um gate de
doc-sync por commit.

> **Times:** o write-gate é imposto por protocolo (agente cooperante + review
> via git). Pra enforcement duro, coloque o vault atrás de **branch protegida
> com PR review obrigatório** — ver o [threat model](docs/ARCHITECTURE.md#threat-model-honest-limits).

## Como funciona (as camadas)

| Camada | Onde | O quê | É verdade? |
|------|-------|------|--------|
| Procedural | `AGENTS.md` / `CLAUDE.md` / `.claude/rules/` | como o agente trabalha aqui | sim (regras) |
| Working memory | roadmap / inbox (briefing derivado de git) | o que está em voo | não (cockpit) |
| Semântica | `knowledge/` + docs oficiais | conceitos & decisões duráveis | sim (durável) |
| Propostas | `insights/` | candidatos "deveríamos?" com score | ainda não |
| Proveniência | `raw/sources/` | fontes ingeridas imutáveis | não (lastro) |

Leituras são **index-first** (LLM-wiki do Karpathy): o agente lê um
`knowledge/index.md` barato, carrega só as páginas relevantes, nunca faz
bulk-read do vault (defesa contra context rot). Escritas passam pelo
**write-gate humano** (`/registra`): o agente propõe, você aprova, o agente
grava e reporta.

## A caixa de ferramentas completa

20 skills (+3 aliases pt-BR), em grupos — adote incrementalmente:

- **Setup (uma vez):** `brain-init`, `brain-router-init`, `brain-scripts-init`,
  `brain-update`.
- **Diário:** `capture`/`registra`, `search`/`busca`, `low-token` (modo enxuto).
- **Pensar:** `challenge` (confronta decisão com reversões passadas),
  `discovery` (leitura ampla delimitada), `spec`, `discover-standards`.
- **Ciclo de vida de insights:** `from-roadmap` → `promote` → `implement` /
  `execute-insight` → `weekly` / `postmortem` / `audit`/`audita`.
- **Manutenção:** `garden`, `archive-closed` (+ o fixer
  `python -m hipocampo.normalize` e o self-test `canary`).

Mais dois hooks (briefing git no SessionStart, capture-sweep no Stop com
redaction de segredos) e nove validators config-driven rodados pelo `preflight`.

## Configuração

Tudo que é específico do projeto vive em **`brain.config.toml`** na raiz —
localização do vault, vocabulário de áreas/status, regras de doc-sync, janela de
decay, gatilhos de captura, idioma. Os scripts leem a config; nada é hardcoded.
Ver [`brain.config.example.toml`](brain.config.example.toml).

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — como funciona (consolidado).
- [PLAN.md](PLAN.md) — fases, decisões, status do port.
- [PUBLISHING.md](PUBLISHING.md) — releases + submissão ao marketplace.
- [CONTRIBUTING.pt-BR.md](CONTRIBUTING.pt-BR.md) — setup + não-negociáveis ([EN](CONTRIBUTING.md)).

## Licença

MIT — ver [`LICENSE`](LICENSE).
