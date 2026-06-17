"""Tests for the enforcement gate (block / warn / off)."""

import unittest
from pathlib import Path

from hipocampo import gate
from hipocampo.config import Config, DEFAULTS, deep_merge


def _cfg(**enforcement):
    return Config(deep_merge(DEFAULTS, {"enforcement": enforcement}), Path("/repo"))


class GateModeTest(unittest.TestCase):
    def test_block_propagates_failure(self):
        rc = gate.run("pre-commit", _cfg(pre_commit="block"), runner=lambda: 1)
        self.assertEqual(rc, 1)

    def test_block_propagates_success(self):
        rc = gate.run("pre-commit", _cfg(pre_commit="block"), runner=lambda: 0)
        self.assertEqual(rc, 0)

    def test_warn_never_blocks_even_on_failure(self):
        rc = gate.run("pre-push", _cfg(pre_push="warn"), runner=lambda: 1)
        self.assertEqual(rc, 0)

    def test_off_skips_runner_entirely(self):
        calls = []

        def runner():
            calls.append(1)
            return 1

        rc = gate.run("pre-commit", _cfg(pre_commit="off"), runner=runner)
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [])  # the check is never even run

    def test_default_point_is_block(self):
        # No [enforcement] override → historical blocking behavior preserved.
        rc = gate.run("ci", Config(DEFAULTS, Path("/repo")), runner=lambda: 1)
        self.assertEqual(rc, 1)

    def test_each_point_reads_its_own_key(self):
        cfg = _cfg(pre_commit="warn", pre_push="block", ci="off")
        self.assertEqual(gate.run("pre-commit", cfg, runner=lambda: 1), 0)  # warn
        self.assertEqual(gate.run("pre-push", cfg, runner=lambda: 1), 1)    # block
        self.assertEqual(gate.run("ci", cfg, runner=lambda: 1), 0)          # off


class GateCliTest(unittest.TestCase):
    def test_unknown_point_is_usage_error(self):
        self.assertEqual(gate.main(["bogus"]), 2)
        self.assertEqual(gate.main([]), 2)

    def test_points_map_to_expected_config_keys(self):
        self.assertEqual({p: k for p, (k, _) in gate._POINTS.items()},
                         {"pre-commit": "pre_commit", "pre-push": "pre_push", "ci": "ci"})


if __name__ == "__main__":
    unittest.main()
