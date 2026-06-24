"""Tests for the deterministic reflection stopping-criteria layer.

The /reflect loop itself lives in the skill (agent-driven, no LLM calls in
Python); only the config plumbing and the stop predicate are unit-testable here.
"""

import tempfile
import unittest
from pathlib import Path

from hipocampo import config
from hipocampo.config import Config, DEFAULTS, deep_merge, load_config
from hipocampo.reflection import StopCriteria, evaluate


def _criteria(max_iterations=3, score_threshold=8, min_improvement=1, patience=1):
    return StopCriteria(max_iterations=max_iterations, score_threshold=score_threshold,
                        min_improvement=min_improvement, patience=patience)


class ReflectionConfigTest(unittest.TestCase):
    def test_defaults(self):
        cfg = Config(DEFAULTS, Path("/repo"))
        self.assertIs(cfg.reflection_enabled, False)        # opt-in
        self.assertEqual(cfg.reflection_max_iterations, 3)
        self.assertEqual(cfg.reflection_score_threshold, 8)
        self.assertEqual(cfg.reflection_score_scale, 10)
        self.assertEqual(cfg.reflection_min_improvement, 1)
        self.assertEqual(cfg.reflection_patience, 1)
        self.assertEqual(cfg.reflection_notes_root, "insights")

    def test_partial_override_keeps_siblings(self):
        merged = deep_merge(DEFAULTS, {"reflection": {"max_iterations": 5}})
        cfg = Config(merged, Path("/repo"))
        self.assertEqual(cfg.reflection_max_iterations, 5)
        self.assertEqual(cfg.reflection_score_threshold, 8)  # sibling survives merge
        self.assertIs(cfg.reflection_enabled, False)

    def test_from_config_reads_criteria(self):
        merged = deep_merge(DEFAULTS, {"reflection": {"max_iterations": 4, "patience": 2}})
        crit = StopCriteria.from_config(Config(merged, Path("/repo")))
        self.assertEqual((crit.max_iterations, crit.score_threshold,
                          crit.min_improvement, crit.patience), (4, 8, 1, 2))

    def _raises_on(self, toml_text):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / config.CONFIG_FILENAME).write_text(toml_text, encoding="utf-8")
            with self.assertRaises(config.ConfigError):
                load_config(start=root)

    def test_invalid_enabled_raises(self):
        self._raises_on('[reflection]\nenabled = "yes"\n')

    def test_negative_int_raises(self):
        self._raises_on("[reflection]\nmin_improvement = -1\n")

    def test_max_iterations_zero_raises(self):
        self._raises_on("[reflection]\nmax_iterations = 0\n")

    def test_threshold_above_scale_raises(self):
        self._raises_on("[reflection]\nscore_threshold = 11\nscore_scale = 10\n")

    def test_bool_for_int_field_raises(self):
        # bool is an int subclass — must be rejected for a numeric knob.
        self._raises_on("[reflection]\nmax_iterations = true\n")

    def test_valid_override_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / config.CONFIG_FILENAME).write_text(
                "[reflection]\nenabled = true\nmax_iterations = 2\n", encoding="utf-8")
            cfg = load_config(start=root)
            self.assertIs(cfg.reflection_enabled, True)
            self.assertEqual(cfg.reflection_max_iterations, 2)


class EvaluateTest(unittest.TestCase):
    def test_empty_scores_continues(self):
        d = evaluate([], _criteria())
        self.assertFalse(d.stop)
        self.assertEqual(d.iterations_done, 0)

    def test_threshold_hit_stops(self):
        d = evaluate([6, 8], _criteria(score_threshold=8))
        self.assertTrue(d.stop)
        self.assertEqual(d.reason, "threshold")

    def test_max_iterations_stops(self):
        d = evaluate([5, 6, 7], _criteria(max_iterations=3, score_threshold=8))
        self.assertTrue(d.stop)
        self.assertEqual(d.reason, "max_iterations")

    def test_convergence_stops_on_flat_scores(self):
        d = evaluate([7, 7], _criteria(min_improvement=1, patience=1, score_threshold=9))
        self.assertTrue(d.stop)
        self.assertEqual(d.reason, "converged")

    def test_degrading_scores_stop_via_convergence(self):
        # a revision that scored LOWER must not keep churning
        d = evaluate([7, 6], _criteria(min_improvement=1, patience=1, score_threshold=9))
        self.assertTrue(d.stop)
        self.assertEqual(d.reason, "converged")

    def test_improving_under_cap_continues(self):
        d = evaluate([5, 7], _criteria(max_iterations=4, score_threshold=9,
                                       min_improvement=1, patience=1))
        self.assertFalse(d.stop)
        self.assertEqual(d.reason, "")

    def test_threshold_takes_precedence_over_max_iterations(self):
        d = evaluate([8, 8, 9], _criteria(max_iterations=3, score_threshold=8))
        self.assertTrue(d.stop)
        self.assertEqual(d.reason, "threshold")

    def test_patience_two_needs_two_flat_rounds(self):
        crit = _criteria(max_iterations=9, score_threshold=99, min_improvement=1, patience=2)
        self.assertFalse(evaluate([5, 5], crit).stop)          # only one delta yet
        self.assertTrue(evaluate([5, 5, 5], crit).stop)        # two flat deltas → converged


if __name__ == "__main__":
    unittest.main()
