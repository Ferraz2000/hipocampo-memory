"""Tests for the opt-in router-lint validator."""

import tempfile
import unittest
from pathlib import Path

from hipocampo.config import Config, DEFAULTS, deep_merge
from hipocampo.validators.router_lint import check_router


def _cfg(root, max_lines=120):
    return Config(deep_merge(DEFAULTS, {"router": {"max_lines": max_lines}}), root)


class RouterLintTest(unittest.TestCase):
    def test_missing_router_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(check_router(_cfg(Path(tmp))), [])

    def test_lean_router_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("\n".join(f"line {i}" for i in range(10)), encoding="utf-8")
            self.assertEqual(check_router(_cfg(root, max_lines=120)), [])

    def test_bloated_router_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("\n".join(f"line {i}" for i in range(200)), encoding="utf-8")
            issues = check_router(_cfg(root, max_lines=120))
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0][0], "FAIL")


if __name__ == "__main__":
    unittest.main()
