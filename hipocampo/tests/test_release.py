"""Tests for the release tooling (pure helpers + drift check)."""

import unittest

from hipocampo import release as r

_CHANGELOG = """\
# Changelog

## [Unreleased]

### Added
- a new thing

## [0.10.0] — 2026-06-18

### Fixed
- an old thing

## [0.9.1]

### Fixed
- older
"""

_README = "**Status: v0.10.0 — usable.** 182 tests, CI green, validated.\n"
_README_PT = "**Status: v0.9.1 — usável.** 145 testes, CI verde.\n"


class BumpTest(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(r.bump("major", "0.10.0"), "1.0.0")
        self.assertEqual(r.bump("minor", "0.10.0"), "0.11.0")
        self.assertEqual(r.bump("patch", "0.10.0"), "0.10.1")

    def test_parse_rejects_garbage(self):
        with self.assertRaises(ValueError):
            r.parse_version("0.10")
        with self.assertRaises(ValueError):
            r.parse_version("v0.10.0")


class PluginVersionTest(unittest.TestCase):
    def test_read_and_set(self):
        text = '{\n  "name": "hipocampo",\n  "version": "0.10.0"\n}\n'
        self.assertEqual(r.plugin_version(text), "0.10.0")
        bumped = r.set_plugin_version(text, "0.11.0")
        self.assertEqual(r.plugin_version(bumped), "0.11.0")
        self.assertIn('"name": "hipocampo"', bumped)  # nothing else touched


class ChangelogTest(unittest.TestCase):
    def test_latest_skips_unreleased(self):
        self.assertEqual(r.latest_changelog_version(_CHANGELOG), "0.10.0")

    def test_promote_opens_fresh_unreleased(self):
        out = r.promote_unreleased(_CHANGELOG, "0.11.0", "2026-06-25")
        # fresh empty Unreleased on top, new version owns the former body
        self.assertIn("## [Unreleased]\n\n## [0.11.0] — 2026-06-25\n", out)
        self.assertEqual(r.latest_changelog_version(out), "0.11.0")
        self.assertIn("- a new thing", r.extract_notes(out, "0.11.0"))

    def test_promote_requires_unreleased(self):
        with self.assertRaises(ValueError):
            r.promote_unreleased("# Changelog\n\n## [0.1.0]\n", "0.2.0", "2026-06-25")

    def test_extract_notes_is_section_scoped(self):
        notes = r.extract_notes(_CHANGELOG, "0.10.0")
        self.assertIn("an old thing", notes)
        self.assertNotIn("a new thing", notes)   # not the Unreleased body
        self.assertNotIn("older", notes)         # not the next section

    def test_extract_notes_missing_version_is_empty(self):
        self.assertEqual(r.extract_notes(_CHANGELOG, "9.9.9"), "")


class StatusLineTest(unittest.TestCase):
    def test_read_version_and_count_both_langs(self):
        self.assertEqual(r.status_line_version(_README), "0.10.0")
        self.assertEqual(r.status_line_count(_README), 182)
        self.assertEqual(r.status_line_version(_README_PT), "0.9.1")
        self.assertEqual(r.status_line_count(_README_PT), 145)

    def test_update_rewrites_version_and_count(self):
        out = r.update_status_line(_README_PT, "0.10.0", 203)
        self.assertEqual(r.status_line_version(out), "0.10.0")
        self.assertEqual(r.status_line_count(out), 203)
        self.assertIn("testes", out)            # language word preserved
        self.assertIn("CI verde", out)          # rest of the line preserved


if __name__ == "__main__":
    unittest.main()
