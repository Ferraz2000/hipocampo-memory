# Publishing hipocampo

The repo is already public and installable as-is. This doc covers cutting a
release and getting it into discovery channels.

## It's already installable

Because `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json` live in
the repo, anyone can install today:

```sh
# Claude Code (plugin: skills + hooks)
/plugin marketplace add Ferraz2000/hipocampo
/plugin install hipocampo@hipocampo

# Cross-agent (Claude Code / Codex / Gemini): just the skills
npx skills add Ferraz2000/hipocampo
```

## Cutting a release

1. Bump `version` in **both** `.claude-plugin/plugin.json` and
   `.claude-plugin/marketplace.json` (semver).
2. Update `PLAN.md` if scope changed; make sure `python -m unittest discover -s
   hipocampo/tests` is green and CI passes.
3. Tag and release:
   ```sh
   git tag -a vX.Y.Z -m "hipocampo vX.Y.Z — <summary>"
   git push origin vX.Y.Z
   gh release create vX.Y.Z --title "hipocampo vX.Y.Z" --notes "<notes>"
   ```
4. Semver matters for installers: a pinned consumer only updates when you bump.
   Omitting a version means every commit is an update — prefer explicit tags.

## Listing in the official community marketplace (for discovery)

`anthropics/claude-plugins-community` is the reviewed, SHA-pinned community
catalog surfaced at claude.com/plugins. To submit:

1. Fork `anthropics/claude-plugins-community`.
2. Add an entry to its `.claude-plugin/marketplace.json` `plugins` array,
   pinning a release commit (use a tag's SHA: `git rev-list -n1 vX.Y.Z`):
   ```json
   {
     "name": "hipocampo",
     "source": {
       "source": "github",
       "repo": "Ferraz2000/hipocampo",
       "sha": "<40-char SHA of the release tag>"
     },
     "description": "Persistent, git-versioned, human-gated memory for coding agents.",
     "category": "productivity",
     "tags": ["memory", "second-brain", "knowledge", "doc-sync"]
   }
   ```
3. Open a PR following that repo's CONTRIBUTING. Their automation validates the
   plugin; once merged, users install via
   `/plugin marketplace add anthropics/claude-plugins-community` →
   `/plugin install hipocampo@claude-plugins-community`.
4. Bumping the kit later = a new PR moving the pinned SHA.

Validate locally before submitting:
```sh
claude plugin validate . --strict   # if the Claude Code CLI is installed
```

## Third-party directories (optional)

Community indexes (e.g. claudemarketplaces.com, awesome-claude-code-plugins) accept
listings that point at this repo's marketplace — additive reach, no code changes.

## Cross-agent note

`npx skills add` already installs the skills into Claude Code, Codex
(`.agents/skills`), and Gemini (`.gemini/skills`). No extra publishing step is
needed for those agents.
