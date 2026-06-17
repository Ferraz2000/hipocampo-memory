"""Tests for the optional [semantic] tier — graceful degradation.

The heavy deps (model2vec / sqlite-vec) are NOT installed in CI, so these cover
the contract that matters for the zero-dep core: when the tier is unavailable,
every entry point is a safe no-op and search is unaffected. The dep-backed paths
(_embed / vec0 queries) are verified separately on a machine with the extra.
"""

import os
import unittest
from pathlib import Path
from unittest import mock

from hipocampo import semantic
from hipocampo.config import Config, DEFAULTS, deep_merge


def _cfg(enabled=False, root="/repo"):
    data = deep_merge(DEFAULTS, {"semantic": {"enabled": enabled}})
    return Config(data, Path(root))


class AvailabilityTest(unittest.TestCase):
    def test_disabled_by_default(self):
        self.assertFalse(semantic.available(_cfg(enabled=False)))

    def test_enabled_but_deps_absent_is_unavailable(self):
        # Deps aren't installed here, so even enabled must report unavailable.
        if semantic._deps() is not None:
            self.skipTest("semantic extra is installed in this env")
        self.assertFalse(semantic.available(_cfg(enabled=True)))

    def test_env_kill_switch_forces_unavailable(self):
        with mock.patch.dict(os.environ, {"HIPOCAMPO_SEMANTIC": "0"}):
            # Even if everything else were satisfied, the kill switch wins.
            with mock.patch.object(semantic, "_deps", return_value=object()), \
                 mock.patch.object(semantic, "extension_loadable", return_value=True):
                self.assertFalse(semantic.available(_cfg(enabled=True)))

    def test_available_true_when_all_conditions_met(self):
        with mock.patch.object(semantic, "_deps", return_value=object()), \
             mock.patch.object(semantic, "extension_loadable", return_value=True):
            self.assertTrue(semantic.available(_cfg(enabled=True)))

    def test_extension_loadable_returns_bool(self):
        self.assertIsInstance(semantic.extension_loadable(), bool)


class NoOpWhenUnavailableTest(unittest.TestCase):
    def setUp(self):
        self.cfg = _cfg(enabled=False)

    def test_rank_returns_empty(self):
        self.assertEqual(semantic.rank("anything", self.cfg), [])

    def test_reindex_returns_zero(self):
        self.assertEqual(semantic.reindex(self.cfg, [("k/a.md", "text")]), 0)

    def test_forget_returns_zero(self):
        self.assertEqual(semantic.forget(self.cfg, ["k/a.md"]), 0)


if __name__ == "__main__":
    unittest.main()
