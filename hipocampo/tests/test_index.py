"""Tests for hipocampo.index — FTS5 build, incremental refresh, prune, RRF.

Skipped wholesale when the local sqlite has no FTS5 (callers fall back to pure
BM25, which test_search covers).
"""

import tempfile
import unittest
from pathlib import Path

from hipocampo import index
from hipocampo.config import Config, DEFAULTS
from hipocampo.index import extract_links, fts5_available, rrf_fuse


class PureHelpersTest(unittest.TestCase):
    def test_rrf_fuse_rewards_agreement(self):
        ordered, scores = rrf_fuse([["a", "b", "c"], ["b", "a", "d"]])
        self.assertEqual(ordered[0], "a")  # top of one list, near-top of the other
        self.assertGreater(scores["a"], scores["c"])

    def test_extract_links_keeps_only_existing_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kn").mkdir()
            (root / "kn" / "a.md").write_text("see [x](b.md) and [y](ghost.md)", encoding="utf-8")
            (root / "kn" / "b.md").write_text("hi", encoding="utf-8")
            links = extract_links("see [x](b.md) and [y](ghost.md)", "kn/a.md", root)
            self.assertEqual(links, ["kn/b.md"])


class Fts5AbsentTest(unittest.TestCase):
    def test_search_falls_back_when_fts5_unavailable(self):
        """Simulate a sqlite build without FTS5: search must use pure BM25."""
        from unittest import mock
        from hipocampo import search as s
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kn = root / "docs/brain/knowledge"
            kn.mkdir(parents=True)
            (kn / "a.md").write_text("onboarding flow", encoding="utf-8")
            cfg = Config(DEFAULTS, root)
            with mock.patch.object(index, "fts5_available", return_value=False):
                results, _ = s.run_search("onboarding", cfg=cfg)  # no no_index flag
            self.assertTrue(results)
            self.assertTrue(results[0][0].endswith("a.md"))
            # and no index file was created (BM25 path, not FTS5)
            self.assertFalse((cfg.cache_dir / "vault-index.sqlite3").exists())


@unittest.skipUnless(fts5_available(), "sqlite without FTS5")
class IndexTest(unittest.TestCase):
    def _vault(self, tmp):
        root = Path(tmp)
        kn = root / "docs/brain/knowledge"
        kn.mkdir(parents=True)
        return Config(DEFAULTS, root), kn

    def test_build_and_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, kn = self._vault(tmp)
            (kn / "a.md").write_text("---\ntitle: Alpha\n---\nonboarding store flow", encoding="utf-8")
            (kn / "b.md").write_text("---\ntitle: Beta\n---\nbilling invoices", encoding="utf-8")
            hits = index.search("onboarding", cfg=cfg)
            self.assertTrue(hits)
            self.assertTrue(hits[0][0].endswith("knowledge/a.md"))

    def test_incremental_refresh_only_reindexes_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, kn = self._vault(tmp)
            (kn / "a.md").write_text("alpha body", encoding="utf-8")
            con = index._connect(cfg)
            try:
                self.assertEqual(index.refresh(con, cfg), 1)   # cold: 1 indexed
                self.assertEqual(index.refresh(con, cfg), 0)   # unchanged: 0
            finally:
                con.close()

    def test_prune_removes_deleted_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, kn = self._vault(tmp)
            note = kn / "a.md"
            note.write_text("onboarding", encoding="utf-8")
            self.assertTrue(index.search("onboarding", cfg=cfg))
            note.unlink()
            self.assertEqual(index.search("onboarding", cfg=cfg), [])

    def test_rrf_surfaces_linked_neighbor(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, kn = self._vault(tmp)
            # a.md matches the query and links to b.md, which does NOT match.
            (kn / "a.md").write_text("onboarding flow\n\nsee [next](b.md)", encoding="utf-8")
            (kn / "b.md").write_text("completely unrelated payments text", encoding="utf-8")
            hits = index.search("onboarding", cfg=cfg, rrf=True)
            paths = [h[0] for h in hits]
            self.assertTrue(any(p.endswith("knowledge/b.md") for p in paths))


if __name__ == "__main__":
    unittest.main()
