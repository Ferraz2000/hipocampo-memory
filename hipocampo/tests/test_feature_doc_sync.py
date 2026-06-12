"""Tests for the doc-sync forcing function (config-driven, glob-matched)."""

import unittest
from pathlib import Path

from hipocampo.config import Config, DEFAULTS, deep_merge
from hipocampo.validators.feature_doc_sync import failures


def _cfg(**over):
    data = deep_merge(DEFAULTS, over)
    return Config(data, Path("/repo"))


RULES = {
    "doc_sync": [
        {"name": "persistence", "paths": ["src/**/migrations/**"],
         "docs": ["docs/architecture/persistence.md"]},
        {"name": "contracts", "paths": ["src/contracts/**"],
         "docs": ["docs/architecture/contracts.md"]},
    ]
}


class DocSyncTest(unittest.TestCase):
    def test_sensitive_change_without_doc_fails(self):
        cfg = _cfg(**RULES)
        fails = failures(["src/app/migrations/001.cs"], cfg)
        self.assertEqual(len(fails), 1)
        self.assertIn("persistence", fails[0])

    def test_sensitive_change_with_matching_doc_passes(self):
        cfg = _cfg(**RULES)
        fails = failures(
            ["src/app/migrations/001.cs", "docs/architecture/persistence.md"], cfg)
        self.assertEqual(fails, [])

    def test_wrong_doc_does_not_satisfy_other_rule(self):
        # contracts changed, but only the persistence doc is staged -> still fails.
        cfg = _cfg(**RULES)
        fails = failures(
            ["src/contracts/x.cs", "docs/architecture/persistence.md"], cfg)
        self.assertEqual(len(fails), 1)
        self.assertIn("contracts", fails[0])

    def test_impact_report_escape_excuses_all_rules(self):
        cfg = _cfg(**RULES)
        fails = failures(
            ["src/app/migrations/001.cs",
             "docs/brain/doc-impact-reports/2026-06-12-note.md"], cfg)
        self.assertEqual(fails, [])

    def test_unrelated_change_passes(self):
        cfg = _cfg(**RULES)
        self.assertEqual(failures(["README.md"], cfg), [])

    def test_no_rules_means_no_failures(self):
        self.assertEqual(failures(["src/app/migrations/001.cs"], _cfg()), [])


if __name__ == "__main__":
    unittest.main()
