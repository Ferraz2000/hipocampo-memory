---
name: reflect
description: Iterate on a work product (code, plan, spec, summary) with an in-session generate→critique→revise loop bounded by config stopping criteria, seeded with past lessons from memory and closed by capturing the distilled lesson. Use when the user says "/reflect", "iterate on this", "critique and improve", "refine until it's good", "reflexion", or asks to keep improving a draft until it meets a bar.
---

# reflect — bounded generate→critique→revise, with memory

The forward-looking, *looping* member of the family. `challenge` confronts a NEW
decision with the past (single pass); `postmortem` mines a FINISHED branch (single
pass); `reflect` iterates on an IN-PROGRESS artifact now, then feeds the lesson
back into durable memory so the next session starts smarter (Reflexion / verbal
reinforcement).

Stopping criteria come from `[reflection]` in `brain.config.toml` — never
improvise the bound. If `[reflection] enabled = false` (the default) or the
section is absent, run ONE critique→revise pass and stop (graceful degrade —
never loop unboundedly).

## Task

1. **Pin the artifact + rubric.** From `$ARGUMENTS` or the conversation, state
   exactly what is being improved and what "good" means (correctness,
   completeness, clarity, …). The score is only as meaningful as the rubric.
2. **Check it's enabled & read the criteria** (deterministic, no improvising):
   `python3 -c "from hipocampo.config import load_config as L; c=L(); print(c.reflection_enabled, c.reflection_max_iterations, c.reflection_score_threshold, c.reflection_score_scale)"`.
   If `reflection_enabled` is `False`, say so, do a single critique→revise pass, and stop.
3. **Seed from memory (the episodic buffer).** Use `recall` /
   `python3 -m hipocampo.search "<concept words>"` to pull prior reflections,
   lessons, and anti-patterns on this topic. Index-first: open only the top 1–3
   pointers. These prior lessons are the verbal-RL gradient — apply them *before*
   the first attempt, don't rediscover them.
4. **Loop** (the cap and criteria are config, not vibes):
   a. **Generate / revise** the artifact, applying the latest critique + recalled lessons.
   b. **Critique against the rubric** (LLM-as-judge — keep the critic mindset
      separate from the creator one): list concrete defects and assign an integer
      score on the configured scale (default 1–10).
   c. **Check the stopping criteria** — shell out with every score so far, in order:
      `python3 -m hipocampo.reflection <score1> <score2> ...`
      It prints `stop=yes|no reason=threshold|max_iterations|converged iterations=N`.
      STOP when it says stop; otherwise fold the critique into the next revision and repeat from (a).
5. **Report** the final artifact, the stop reason, and the score trajectory (e.g. `6 → 8`).
6. **Distill + capture the lesson (close the loop).** Write ONE durable,
   generalizable lesson from this iteration ("X failed because Y; prefer Z") and
   propose filing it via `capture` (it classifies → files under `[reflection]
   notes_root`, default `insights/<area>/`, or `knowledge/` if it's a stable
   concept → index → log). The human write-gate is theirs: propose, don't auto-file.
7. **If the loop surfaced a conflict with a past decision**, name it and suggest
   `/challenge` rather than resolving it here.

## Rules

- The bound is config — always defer to `hipocampo.reflection`. Default cap is 3;
  returns diminish sharply after that.
- Degrade, don't fail: `[reflection]` absent or `enabled = false` ⇒ single pass, no loop.
- Don't reinvent search or filing — `reflect` calls `recall` to read and `capture`
  to write. It owns only the loop and the stop check.
- Score honestly. A revision that scores *lower* than the prior one trips the
  convergence stop — keep the best version, don't churn a degrading artifact.
- Don't reflect the trivial — each iteration is extra latency/tokens.
- No secrets in the distilled lesson; redact before `capture` files it.
- Read bounded (the episodic seed is a search, not a vault sweep).
