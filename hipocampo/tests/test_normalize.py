"""Tests for hipocampo.normalize — vocabulary fixer."""

import unittest

from hipocampo.normalize import normalize_text


class NormalizeTest(unittest.TestCase):
    def test_grade_synonyms_fixed(self):
        text = "---\ntype: insight\nimpact: alto\neffort: baixa\n---\nalto body untouched\n"
        new, changes = normalize_text(text, {})
        self.assertIn("impact: high\n", new)
        self.assertIn("effort: low\n", new)
        self.assertIn("alto body untouched", new)
        self.assertEqual(len(changes), 2)

    def test_area_alias_fixed_but_spec_untouched(self):
        aliases = {"api": "Core.API"}
        new, ch = normalize_text("---\ntype: insight\narea: api\n---\n", aliases)
        self.assertIn("area: Core.API\n", new)
        new2, ch2 = normalize_text("---\ntype: spec\narea: api\n---\n", aliases)
        self.assertEqual(ch2, [])

    def test_unknown_values_left_alone(self):
        new, ch = normalize_text("---\nimpact: weird\n---\n", {})
        self.assertEqual(ch, [])
        self.assertIn("impact: weird", new)

    def test_no_frontmatter_noop(self):
        self.assertEqual(normalize_text("plain text", {}), ("plain text", []))


if __name__ == "__main__":
    unittest.main()
