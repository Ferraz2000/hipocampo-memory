"""Tests for the doc-links validator."""

import tempfile
import unittest
from pathlib import Path

from hipocampo.validators.doc_links import broken_doc_links, missing_required_docs


class DocLinksTest(unittest.TestCase):
    def test_broken_relative_link_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.md").write_text("see [x](missing.md)", encoding="utf-8")
            broken = broken_doc_links(root)
            self.assertEqual([t for _, t in broken], ["missing.md"])

    def test_resolving_link_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.md").write_text("see [x](b.md)", encoding="utf-8")
            (root / "b.md").write_text("hi", encoding="utf-8")
            self.assertEqual(broken_doc_links(root), [])

    def test_commented_link_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.md").write_text("<!-- example: [x](ghost.md) -->\nreal text\n", encoding="utf-8")
            self.assertEqual(broken_doc_links(root), [])

    def test_fenced_link_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.md").write_text("```\n[x](ghost.md)\n```\n", encoding="utf-8")
            self.assertEqual(broken_doc_links(root), [])

    def test_excluded_dir_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "node_modules").mkdir()
            (root / "node_modules" / "a.md").write_text("[x](ghost.md)", encoding="utf-8")
            self.assertEqual(broken_doc_links(root, {"node_modules"}), [])
            # without excluding it, the broken link is found
            self.assertEqual([t for _, t in broken_doc_links(root)], ["ghost.md"])

    def test_missing_required_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(missing_required_docs(root, ["docs/x.md"]), ["docs/x.md"])


if __name__ == "__main__":
    unittest.main()
