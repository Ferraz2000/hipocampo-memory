---
name: discover-standards
description: Mine the existing codebase for de-facto conventions (naming, structure, error handling, test patterns) and propose them as candidate insights for the vault. Use when the user says "/discover-standards", "extract our conventions", "what patterns do we follow".
---

# discover-standards — mine the code for conventions

Complements `registra` (which captures from conversation) and `postmortem` (which
captures from a branch): this one captures from the **code itself**. Inspired by
Agent OS's "Discover".

## Task

1. **Sample the codebase** (read-only, bounded): pick representative files across
   the main subsystems — don't read everything. Prefer a read-only sub-agent for
   the sweep, returning a summary.
2. **Extract recurring conventions**, e.g.:
   - naming (files, types, tests), directory/module structure,
   - error handling, validation style, logging,
   - test patterns (framework, naming, fixtures), API/endpoint shape.
   Note where each is consistent vs where the code disagrees with itself.
3. **Propose each as a candidate insight** under `<vault>/insights/<area>/` with
   `status: triage` — a one-line convention + 2–3 example file paths as evidence.
   Don't write them as truth; they're proposals for the user to confirm.
4. **Report** the list with confidence (how consistently each holds) and flag the
   inconsistencies worth resolving.

## Rules

- Evidence-based: every proposed standard cites real file paths. No invented rules.
- Bounded reading (context budget). Capturing to the vault still goes through the
  `registra`/discovery write-gate — propose, the user confirms.
