# hipocampo

🌐 **Português** · [English](README.md)

**Memória persistente, versionada em git e com write-gate humano para agentes de
código.** Seus agentes (Claude Code, Codex, Gemini) param de esquecer entre
sessões e de deixar docs apodrecerem — em qualquer projeto, qualquer linguagem.

> *Hipocampo* é a região do cérebro que consolida memória de curto prazo em
> longo prazo. O kit faz o mesmo: capturas cruas caem num `_inbox/`, e um
> pipeline com write-gate as transforma numa base `knowledge/` curada e
> auditável, que vive no seu repo e se compõe ao longo do tempo.

**Status: v0.8.3 — usável.** 107 testes, CI verde, validado ponta-a-ponta cinco
vezes, incluindo um projeto de produção como primeiro consumidor
([detalhes](PLAN.md)).

## Quickstart (2 minutos)

```sh
/plugin marketplace add Ferraz2000/hipocampo-memory     # Claude Code (skills + hooks)
/plugin install hipocampo@hipocampo
# ou cross-agent (Claude Code / Codex / Gemini) — as skills instalam nativamente:
npx skills add Ferraz2000/hipocampo-memory
```

No Codex e no Gemini as skills são lidas nativamente (sem wrapper); o
`brain-scripts-init` também conecta os hooks de sessão neles. Veja
[Suporte cross-agent](#suporte-cross-agent).

Aí diga `/brain-init` no seu projeto. **O agente faz o setup** — ele te faz três
perguntas (idioma, onde fica o vault, áreas iniciais), gera a config e scaffolda
o vault. Daí em diante, o dia-a-dia é só conversar:

```
/capture <algo>     # "lembra dessa decisão" → vira nota revisável
/search <termos>    # "o que a gente sabe sobre X?"
```

Só isso pra começar. Todo o resto é opcional e **o agente roda por você** — veja
[a caixa de ferramentas completa](#a-caixa-de-ferramentas-completa).

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
  Update one of: docs/architecture/persistence.md
$ git add docs/architecture/persistence.md && git commit ...   # passa
```

E a memória vira **diff revisável**, não caixa-preta:

```diff
+ docs/brain/knowledge/architecture/error-style.md   # /capture escreveu isto
+ docs/brain/knowledge/index.md                       # +1 linha no índice
```

Agente propõe → você aprova → cai no git. Validators mantêm honesto;
`python -m hipocampo.canary` prova que os gates mordem contra o *seu* setup.

## Como funciona

Um princípio: **o humano cura conversando; o agente faz o bookkeeping.**

| Camada | Onde | É verdade? |
|------|-------|--------|
| Regras (como trabalhar aqui) | `AGENTS.md` / `.claude/rules/` | sim |
| Working memory (em voo) | briefing de sessão derivado de git | não (cockpit) |
| Conhecimento durável | `knowledge/` + docs oficiais | sim |
| Propostas ("deveríamos?") | `insights/` (com score) | ainda não |
| Proveniência | `raw/sources/` (imutável) | lastro |

Leituras são **index-first**: o agente lê um `knowledge/index.md` barato e
carrega só as páginas relevantes — nunca o vault inteiro (defesa contra context
rot). Escritas passam pelo **write-gate humano** (`/capture`): o agente propõe,
você aprova, o agente grava e reporta.

## O que cai no seu repo

`/brain-init` + `/brain-scripts-init` adicionam, e o agente mantém:

```
brain.config.toml     # todas as settings do projeto (gerado, não escrito à mão)
docs/brain/           # o vault: knowledge/, insights/, raw/sources/, templates
hipocampo/            # scripts zero-dependência vendorados (busca, gates, hooks)
.githooks/            # pre-commit (gate de doc-sync) + pre-push (preflight)
.github/workflows/    # opcional: os mesmos gates no CI
```

Markdown puro + Python stdlib. Sem daemon, sem banco, sem pip install — apagou
as pastas, sumiu.

## A caixa de ferramentas completa

20 skills, em grupos — **você não decora isso; o agente escolhe a partir do que
você diz.** Adote incrementalmente:

- **Setup (uma vez):** `brain-init`, `brain-router-init`, `brain-scripts-init`, `brain-update`.
- **Diário:** `capture`, `search`, `low-token` (modo enxuto).
- **Pensar:** `challenge` (confronta decisão com reversões passadas), `discovery`, `spec`, `discover-standards`.
- **Ciclo de vida de insights:** `from-roadmap` → `promote` → `implement` / `execute-insight` → `weekly` / `postmortem` / `audit`.
- **Manutenção:** `garden`, `archive-closed` (+ o fixer `normalize` e o self-test `canary`).

Mais dois hooks de sessão (briefing git no início; capture-sweep no fim, com
redaction de segredos) — conectados por agente — e seis validators config-driven
rodados pelo `preflight`.

## Suporte cross-agent

Um kit, adaptadores finos por agente. O núcleo portátil (as 20 skills SKILL.md, o
router `AGENTS.md`, o pacote Python zero-dep, git-hooks + CI) roda em qualquer
lugar; os automatismos de sessão são conectados ao sistema de hooks nativo de cada
agente.

| Capacidade | Claude Code | Codex CLI | Gemini CLI |
|------------|-------------|-----------|------------|
| Skills (SKILL.md) | nativo | nativo (`.agents/skills`) | nativo (`.gemini/skills`) |
| Router (`AGENTS.md`) | via `CLAUDE.md → @AGENTS.md` | auto-descoberto | setar `context.fileName` em `.gemini/settings.json` |
| Briefing no início da sessão | hook `SessionStart` | hook `SessionStart` | hook `SessionStart` |
| Capture-sweep no fim | hook `Stop` | hook `Stop` | hook `SessionEnd` |
| Memória de persona | `.claude/rules/USER.md` (auto-load) | arquivo apontado pelo `AGENTS.md` | arquivo apontado pelo `AGENTS.md` |
| Regras por path | nativo (`.claude/rules/*.md` `paths:`) | dobrar no `AGENTS.md` | dobrar no `AGENTS.md` |
| Gate de doc-sync, busca, validators | ✅ (Python vendorado) | ✅ | ✅ |

Notas: os hooks do Codex são **experimentais** (o formato de transcript não é
estável — o sweep degrada graciosamente). A chave de router do Gemini é
`context.fileName` (builds antigos: `contextFileName`). O caminho da persona é
configurável via `[memory] persona_file` no `brain.config.toml`.

## Configuração

Tudo que é específico do projeto vive em **`brain.config.toml`** na raiz.
**Você não escreve isso à mão** — o `/brain-init` gera a partir de três
respostas, e você evolui pedindo ao agente ("adiciona regra de doc-sync pra
`src/api/`", "sobe a janela de decay pra 60 dias"). O schema completo, pra
auditoria ou edição manual: [`brain.config.example.toml`](brain.config.example.toml).

## Por que isto e não um framework de memória

O estado da arte 2025–2026 convergiu pra **markdown como fonte de verdade + um
índice derivado opcional** (auto-memory da Anthropic, MemFS do Letta Code,
basic-memory — independentemente). Memória em DB abre mão da auditabilidade por
git-diff. O hipocampo adiciona a peça que nenhum framework publicado entrega
bem: **governança** — write-gate humano, frontmatter-como-verdade e um gate de
doc-sync por commit.

> **Times:** o write-gate é imposto por protocolo (agente cooperante + review
> via git). Pra enforcement duro, coloque o vault atrás de **branch protegida
> com PR review obrigatório** — ver o [threat model](docs/ARCHITECTURE.md#threat-model-honest-limits).

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — como funciona (consolidado).
- [PLAN.md](PLAN.md) — fases, decisões, histórico de validação.
- [PUBLISHING.md](PUBLISHING.md) — releases + submissão ao marketplace.
- [CONTRIBUTING.pt-BR.md](CONTRIBUTING.pt-BR.md) — setup, layout interno do kit, não-negociáveis ([EN](CONTRIBUTING.md)).

## Licença

MIT — ver [`LICENSE`](LICENSE).
