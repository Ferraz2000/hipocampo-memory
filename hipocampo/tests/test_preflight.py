"""Tests for the preflight runner — validator dispatch, skip, and failure roll-up.

The runner's own logic is isolated from real validators by injecting fake
validator modules into ``sys.modules`` (``importlib.import_module`` returns those
without touching disk) and stubbing ``load_config``.
"""

import sys
import types
import unittest
from pathlib import Path
from unittest import mock

from hipocampo import preflight
from hipocampo.config import Config, ConfigError, DEFAULTS, deep_merge


def _cfg(validators):
    return Config(deep_merge(DEFAULTS, {"validators": validators}), Path("/repo"))


def _fake_validator(name, rc):
    mod = types.ModuleType(f"hipocampo.validators.{name}")
    if isinstance(rc, Exception):
        def _main(argv):
            raise rc
    else:
        def _main(argv):
            return rc
    mod.main = _main
    return {f"hipocampo.validators.{name}": mod}


class PreflightTest(unittest.TestCase):
    def _run(self, cfg, injected=None):
        with mock.patch("hipocampo.config.load_config", return_value=cfg), \
                mock.patch.dict(sys.modules, injected or {}):
            return preflight.main([])

    def test_no_validators_configured_is_ok(self):
        self.assertEqual(self._run(_cfg([])), 0)

    def test_unknown_validator_is_skipped_not_failed(self):
        # A name with no matching module SKIPs (not a failure) → still exit 0.
        self.assertEqual(self._run(_cfg(["definitely_not_a_validator"])), 0)

    def test_passing_validator_returns_zero(self):
        self.assertEqual(self._run(_cfg(["okcheck"]), _fake_validator("okcheck", 0)), 0)

    def test_failing_validator_returns_one(self):
        self.assertEqual(self._run(_cfg(["badcheck"]), _fake_validator("badcheck", 1)), 1)

    def test_mixed_set_fails_if_any_fails(self):
        injected = {**_fake_validator("ok1", 0), **_fake_validator("bad1", 1)}
        self.assertEqual(self._run(_cfg(["ok1", "bad1"]), injected), 1)

    def test_validator_config_error_counts_as_failure(self):
        injected = _fake_validator("boom", ConfigError("bad rule"))
        self.assertEqual(self._run(_cfg(["boom"]), injected), 1)

    def test_load_config_error_is_reported_and_fails(self):
        with mock.patch("hipocampo.config.load_config",
                        side_effect=ConfigError("unreadable")):
            self.assertEqual(preflight.main([]), 1)


if __name__ == "__main__":
    unittest.main()
