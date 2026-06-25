"""Deterministic stopping-criteria evaluation for the `/reflect` loop.

NO LLM calls. The `/reflect` SKILL drives the generate->critique->revise loop and
produces the per-iteration rubric scores; this module only answers, given those
scores and the configured criteria, whether the loop should stop and why. This
mirrors :mod:`hipocampo.gate`: the policy decision lives here in deterministic
Python, the reasoning (judging, revising) lives in the agent/skill.

Stopping criteria come from the ``[reflection]`` table in ``brain.config.toml``
(never hardcoded in the skill prose). Precedence, highest first:

1. ``threshold``       — the latest score reached ``score_threshold`` (early win).
2. ``max_iterations``  — the hard cap was reached (the primary safety control).
3. ``converged``       — no gain >= ``min_improvement`` over the last ``patience``
                         rounds (covers the "revisions stopped helping / are
                         degrading" case).

CLI (so the skill can shell out, same ergonomics as ``hipocampo.search``):

    $ python3 -m hipocampo.reflection 6 7 8
    stop=yes reason=threshold iterations=3
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from .config import ConfigError, load_config


@dataclass(frozen=True)
class StopCriteria:
    """The four knobs that decide when the loop ends (read from config)."""

    max_iterations: int
    score_threshold: int
    min_improvement: int
    patience: int

    @classmethod
    def from_config(cls, cfg) -> "StopCriteria":
        return cls(
            max_iterations=cfg.reflection_max_iterations,
            score_threshold=cfg.reflection_score_threshold,
            min_improvement=cfg.reflection_min_improvement,
            patience=cfg.reflection_patience,
        )


@dataclass(frozen=True)
class StopDecision:
    stop: bool
    reason: str          # "" | "threshold" | "max_iterations" | "converged"
    iterations_done: int


def evaluate(scores, criteria: StopCriteria) -> StopDecision:
    """Decide whether the loop should stop, given the rubric score after each
    completed iteration (in order). Empty ``scores`` => don't stop (the loop has
    not run yet). See the module docstring for precedence."""
    n = len(scores)
    if n == 0:
        return StopDecision(False, "", 0)
    if scores[-1] >= criteria.score_threshold:
        return StopDecision(True, "threshold", n)
    if n >= criteria.max_iterations:
        return StopDecision(True, "max_iterations", n)
    # Convergence needs `patience` deltas, i.e. `patience + 1` scores. A delta
    # below `min_improvement` (including a negative one — a degrading revision)
    # counts as no progress.
    if criteria.patience >= 1 and n >= criteria.patience + 1:
        recent = scores[-(criteria.patience + 1):]
        deltas = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]
        if all(d < criteria.min_improvement for d in deltas):
            return StopDecision(True, "converged", n)
    return StopDecision(False, "", n)


def main(argv=None) -> int:
    """CLI: ``python3 -m hipocampo.reflection <score> [score ...]``.

    Prints one ``stop=… reason=… iterations=…`` line for the skill to read.
    Always returns 0 — it reports, it does not gate."""
    args = sys.argv[1:] if argv is None else list(argv)
    try:
        scores = [int(a) for a in args]
    except ValueError:
        print("usage: python -m hipocampo.reflection <score> [score ...]  (integers)",
              file=sys.stderr)
        return 0
    try:
        criteria = StopCriteria.from_config(load_config())
    except ConfigError as exc:
        print(f"reflection: config error: {exc}", file=sys.stderr)
        return 0
    decision = evaluate(scores, criteria)
    print(f"stop={'yes' if decision.stop else 'no'} "
          f"reason={decision.reason or '-'} iterations={decision.iterations_done}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
