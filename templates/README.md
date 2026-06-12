# templates/ — scaffolded into target repos (WIP, Phase 5)

The generator skills copy from here into a target project (idempotent, never
overwriting existing `.md`):

- `vault/` — the `docs/brain/` skeleton: `knowledge/index.md`, `capture.md`
  (capture protocol + write-gate), `context-budget.md` (index-first, never
  bulk-read), `README.md` (canonical frontmatter), empty `insights/`,
  `raw/sources/`, `knowledge/_inbox/`.
- `githooks/` — `pre-commit` (doc-sync gate + view regeneration) and `pre-push`
  (preflight).
- `ci/` — the `agent-docs` workflow that runs preflight.

Content is authored in English and parameterized by the `language` key in
`brain.config.toml`. Empty until Phase 5 — see [`../PLAN.md`](../PLAN.md).
