"""Tests for the shared markdown helpers (title extraction + .md walking)."""

import tempfile
import unittest
from pathlib import Path

from hipocampo import index, search
from hipocampo.mdutil import iter_md, iter_vault_md, title_of


class TitleOfTest(unittest.TestCase):
    def test_prefers_frontmatter_title(self):
        self.assertEqual(title_of("---\ntitle: From FM\n---\n# Heading\n", "fb"), "From FM")

    def test_falls_back_to_first_h1(self):
        self.assertEqual(title_of("# An H1 Heading\n\nbody", "fb"), "An H1 Heading")

    def test_strips_quotes_on_frontmatter_title(self):
        self.assertEqual(title_of("title: 'Quoted'\n", "fb"), "Quoted")

    def test_uses_fallback_when_no_title_or_heading(self):
        self.assertEqual(title_of("just body text\n## not an h1", "fb.md"), "fb.md")

    def test_ignores_hash_mid_line(self):
        self.assertEqual(title_of("text with # mid-line", "fb"), "fb")

    def test_back_compat_aliases_point_at_the_shared_impl(self):
        # search.title_of and index.extract_title are re-exports of the one impl.
        self.assertIs(search.title_of, title_of)
        self.assertIs(index.extract_title, title_of)


class IterMdTest(unittest.TestCase):
    def test_walks_recursively_and_filters_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sub").mkdir()
            (root / "a.md").write_text("x", encoding="utf-8")
            (root / "sub" / "b.md").write_text("x", encoding="utf-8")
            (root / "c.txt").write_text("x", encoding="utf-8")
            found = sorted(Path(p).name for p in iter_md(root))
            self.assertEqual(found, ["a.md", "b.md"])

    def test_missing_directory_yields_nothing(self):
        self.assertEqual(list(iter_md(Path("/no/such/dir"))), [])

    def test_sorted_within_a_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("c.md", "a.md", "b.md"):
                (root / name).write_text("x", encoding="utf-8")
            names = [Path(p).name for p in iter_md(root)]
            self.assertEqual(names, ["a.md", "b.md", "c.md"])

    def test_iter_vault_md_resolves_dirs_against_vault_root(self):
        from hipocampo.config import Config, DEFAULTS
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kn = root / "docs/brain/knowledge"
            kn.mkdir(parents=True)
            (kn / "note.md").write_text("x", encoding="utf-8")
            cfg = Config(DEFAULTS, root)
            found = list(iter_vault_md(cfg, ["knowledge"]))
            self.assertEqual(len(found), 1)
            self.assertTrue(found[0].endswith("note.md"))


if __name__ == "__main__":
    unittest.main()
