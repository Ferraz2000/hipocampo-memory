"""Tests for hipocampo.globs — gitignore-style ** path matching."""

import unittest

from hipocampo.globs import match, match_any


class GlobTest(unittest.TestCase):
    def test_double_star_matches_any_depth(self):
        self.assertTrue(match("src/Core/x.cs", "src/Core/**"))
        self.assertTrue(match("src/Core/a/b/x.cs", "src/Core/**"))

    def test_leading_segments_optional(self):
        self.assertTrue(match("src/app/migrations/001.cs", "src/**/migrations/**"))
        self.assertTrue(match("src/migrations/001.cs", "src/**/migrations/**"))

    def test_single_star_does_not_cross_slash(self):
        self.assertTrue(match("docs/a.md", "docs/*.md"))
        self.assertFalse(match("docs/sub/a.md", "docs/*.md"))

    def test_impact_report_escape_glob(self):
        self.assertTrue(match("docs/brain/doc-impact-reports/2026-06-12-x.md",
                              "**/doc-impact-reports/**/*.md"))

    def test_match_any(self):
        self.assertTrue(match_any("a/b.py", ["x/**", "a/*.py"]))
        self.assertFalse(match_any("a/b.py", ["x/**", "c/*.py"]))


if __name__ == "__main__":
    unittest.main()
