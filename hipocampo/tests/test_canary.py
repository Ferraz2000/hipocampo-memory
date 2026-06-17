"""Tests for the canary — the adversarial self-test of the governance gates.

Builds synthetic configs and drives ``_scenarios``/``main`` directly so the test
never depends on the repo's own brain.config.toml.
"""

import unittest
from pathlib import Path
from unittest import mock

from hipocampo import canary
from hipocampo.config import Config, ConfigError, DEFAULTS, deep_merge

_DOC_SYNC = [{"name": "persistence", "paths": ["src/db/**"], "docs": ["docs/db.md"]}]


def _cfg(**overrides):
    return Config(deep_merge(DEFAULTS, overrides), Path("/repo"))


class SynthPathTest(unittest.TestCase):
    def test_plain_path_is_unchanged(self):
        self.assertEqual(canary._synth_path("docs/db.md"), "docs/db.md")

    def test_doublestar_and_star_segments_become_concrete(self):
        self.assertEqual(canary._synth_path("src/db/**"), "src/db/canary/canary.txt")
        self.assertEqual(canary._synth_path("src/**/*.py"), "src/canary/canary.py")

    def test_extensionless_tail_gets_a_filename(self):
        self.assertTrue(canary._synth_path("src/db/**").endswith("canary.txt"))


class ScenariosTest(unittest.TestCase):
    def test_every_runnable_scenario_behaves_as_expected(self):
        cfg = _cfg(doc_sync=_DOC_SYNC)
        ran = 0
        for name, run, expect in canary._scenarios(cfg):
            if run is None:
                continue
            ran += 1
            self.assertEqual(run(), expect, msg=name)
        self.assertGreaterEqual(ran, 6)  # 3 doc-sync + 3 vault + 1 doc-links (minus skips)

    def test_doc_sync_scenarios_are_skipped_without_rules(self):
        cfg = _cfg()  # DEFAULTS: doc_sync == []
        scenarios = list(canary._scenarios(cfg))
        names = [n for n, _, _ in scenarios]
        self.assertTrue(any(run is None for _, run, _ in scenarios))
        self.assertTrue(any("no [[doc_sync]] rules" in n for n in names))


class MainTest(unittest.TestCase):
    def test_main_exits_zero_when_all_gates_bite(self):
        cfg = _cfg(doc_sync=_DOC_SYNC)
        with mock.patch("hipocampo.config.load_config", return_value=cfg):
            self.assertEqual(canary.main(), 0)

    def test_main_reports_config_error(self):
        with mock.patch("hipocampo.config.load_config",
                        side_effect=ConfigError("bad config")):
            self.assertEqual(canary.main(), 1)

    def test_main_exits_one_when_a_gate_fails_to_bite(self):
        cfg = _cfg(doc_sync=_DOC_SYNC)
        # Force feature_doc_sync to never report a failure → the "MUST FAIL"
        # scenario no longer bites, so the canary must flag a broken gate.
        with mock.patch("hipocampo.config.load_config", return_value=cfg), \
                mock.patch("hipocampo.validators.feature_doc_sync.failures",
                           return_value=[]):
            self.assertEqual(canary.main(), 1)


if __name__ == "__main__":
    unittest.main()
