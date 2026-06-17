"""Tests for the vendored frontmatter parser (stdlib, zero-dep)."""

import unittest

from hipocampo.frontmatter import parse_frontmatter


class ParseFrontmatterTest(unittest.TestCase):
    def test_no_frontmatter_returns_empty_and_full_text(self):
        fields, body = parse_frontmatter("# Just a heading\nbody")
        self.assertEqual(fields, {})
        self.assertEqual(body, "# Just a heading\nbody")

    def test_scalar_fields_are_parsed_and_unquoted(self):
        fields, body = parse_frontmatter("---\ntitle: 'Hello'\nstatus: active\n---\nbody\n")
        self.assertEqual(fields["title"], "Hello")
        self.assertEqual(fields["status"], "active")
        self.assertEqual(body, "body\n")

    def test_list_block_collects_items_under_its_key(self):
        text = "---\nsources:\n  - raw/sources/a.md\n  - raw/sources/b.md\n---\n"
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["sources"], ["raw/sources/a.md", "raw/sources/b.md"])

    def test_empty_scalar_then_non_list_line_stays_empty_string(self):
        fields, _ = parse_frontmatter("---\nnotes:\ntitle: T\n---\n")
        self.assertEqual(fields["notes"], "")
        self.assertEqual(fields["title"], "T")

    def test_unterminated_block_is_treated_as_no_frontmatter(self):
        text = "---\ntitle: T\nno closing delimiter\n"
        fields, body = parse_frontmatter(text)
        self.assertEqual(fields, {})
        self.assertEqual(body, text)

    def test_body_preserves_trailing_newline_flag(self):
        _, body_nl = parse_frontmatter("---\na: 1\n---\nx\n")
        _, body_no = parse_frontmatter("---\na: 1\n---\nx")
        self.assertTrue(body_nl.endswith("\n"))
        self.assertFalse(body_no.endswith("\n"))

    def test_empty_input(self):
        self.assertEqual(parse_frontmatter(""), ({}, ""))


if __name__ == "__main__":
    unittest.main()
