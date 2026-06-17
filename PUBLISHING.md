# Publishing hipocampo

The repo is already public and installable as-is. This doc covers cutting a
release and getting it into discovery channels.

## It's already installable

Because `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json` live in
the repo, anyone can install today:

```sh
# Claude Code (plugin: skills + hooks)
/plugin marketplace add Ferraz2000/hipocampo-memory
/plugin install hipocampo@hipocampo

# Cross-agent (Claude Code / Codex / Gemini): just the skills
npx skills add Ferraz2000/hipocampo-memory
```

## Cutting a release

1. Bump `version` in **both** `.claude-plugin/plugin.json` and
   `.claude-plugin/marketplace.json` (semver). **Check the README's Status line
   and skill/validator counts still match reality** — README drift is the one
   thing no validator catches.
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

`anthropics/claude-plugins-community` is a **read-only mirror** of Anthropic's
internal review pipeline — PRs against it are closed automatically. To get
listed (surfaced at claude.com/plugins and installable via
`claude plugin install hipocampo@claude-community`):

1. Submit the repo URL via the official form:
   **https://clau.de/plugin-directory-submission** (claude.ai account).
2. Before submitting, make sure `claude plugin validate . --strict` passes and
   the release you want listed is tagged (the pipeline pins a commit SHA).
3. Updates flow the same way — resubmit/notify with the new release.

## Third-party directories (optional)

Community indexes (e.g. claudemarketplaces.com, awesome-claude-code-plugins) accept
listings that point at this repo's marketplace — additive reach, no code changes.

## Cross-agent note

`npx skills add` installs the skills natively into Claude Code, Codex
(`.agents/skills`), and Gemini (`.gemini/skills`) — all three read the SKILL.md
format directly, no wrapper. No extra publishing step is needed for those agents.

The session hooks (briefing + capture-sweep) are not carried by the Claude Code
plugin manifest, so on Codex/Gemini they're wired by `brain-scripts-init` from
`templates/hooks/{codex,gemini}/` into the agent's own hook config
(`.codex/hooks.json` / `.gemini/settings.json`). See the
[cross-agent matrix](README.md#cross-agent-support).
