---
name: challenge
description: Before committing to a decision or approach, confront it with the vault's past reversals, failures, and superseded decisions on the same topic. Use when the user says "/challenge", "has this been tried", "did we decide against this", or before a significant architectural choice.
---

# challenge — confront a decision with the vault's history

Surface prior art before the project repeats a mistake. Uses the accumulated
`knowledge/` + `insights/` as institutional memory.

## Task

1. **Extract the proposed decision** from the conversation (or `$ARGUMENTS`).
2. **Search the vault** for related history:
   `python3 -m hipocampo.search "<decision keywords>" --all` (`--all` includes
   terminal-status notes — rejected/superseded/closed are exactly what matters here).
3. **Filter to contradictions/precedents**: notes with `status: rejected` /
   `superseded` / `closed`, decisions whose `valid_until` passed, or `knowledge/`
   pages whose conclusion conflicts with the proposal.
4. **Report**, concisely:
   - prior decisions that **reversed or rejected** something similar (with why),
   - decisions this would **contradict or supersede** (link them),
   - if nothing relevant: say so plainly — "no prior art found", don't invent.
5. If the user proceeds anyway and it supersedes an existing decision, offer to
   capture the change via `capture` (set the old page's `superseded_by`).

## Rules

- Read bounded (this is a search, not a vault sweep). Report; don't decide for the user.
- Quote the prior note's path so the user can open it.
