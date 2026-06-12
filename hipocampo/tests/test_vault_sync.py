"""Tests for the vault-sync validator: index consistency, vocab, provenance."""

import tempfile
import unittest
from pathlib import Path

from hipocampo.config import Config, DEFAULTS
from hipocampo.validators import vault_sync


def _levels(issues):
    return sorted(level for level, _ in issues)


class VaultSyncTest(unittest.TestCase):
    def _vault(self, tmp):
        root = Path(tmp)
        v = root / "docs/brain"
        (v / "knowledge").mkdir(parents=True)
        (v / "insights").mkdir(parents=True)
        (v / "raw/sources").mkdir(parents=True)
        return Config(DEFAULTS, root), v

    # -- knowledge index --------------------------------------------------
    def test_page_without_index_entry_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, v = self._vault(tmp)
            (v / "knowledge/index.md").write_text("# index\n", encoding="utf-8")
            (v / "knowledge/meta").mkdir()
            (v / "knowledge/meta/note.md").write_text("# note\n", encoding="utf-8")
            issues = vault_sync.check_knowledge_index(cfg)
            self.assertEqual(_levels(issues), ["FAIL"])

    def test_page_with_index_entry_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, v = self._vault(tmp)
            (v / "knowledge/meta").mkdir()
            (v / "knowledge/meta/note.md").write_text("# note\n", encoding="utf-8")
            (v / "knowledge/index.md").write_text(
                "- [note](meta/note.md) — hook\n", encoding="utf-8")
            self.assertEqual(vault_sync.check_knowledge_index(cfg), [])

    def test_index_link_to_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, v = self._vault(tmp)
            (v / "knowledge/index.md").write_text(
                "- [ghost](meta/ghost.md)\n", encoding="utf-8")
            issues = vault_sync.check_knowledge_index(cfg)
            self.assertTrue(any("ghost" in m for _, m in issues))

    # -- status / area vocabulary ----------------------------------------
    def test_offvocab_status_and_area_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, v = self._vault(tmp)
            (v / "insights/x.md").write_text(
                "---\ntype: insight\nstatus: bogus\narea: nonsense\n---\n",
                encoding="utf-8")
            issues = vault_sync.check_status_area(cfg)
            self.assertEqual(len(issues), 2)
            self.assertTrue(all(l == "FAIL" for l, _ in issues))

    def test_spec_type_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, v = self._vault(tmp)
            (v / "insights/s.md").write_text(
                "---\ntype: spec\nstatus: whatever\n---\n", encoding="utf-8")
            self.assertEqual(vault_sync.check_status_area(cfg), [])

    # -- provenance -------------------------------------------------------
    def test_missing_source_fails_and_orphan_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, v = self._vault(tmp)
            (v / "knowledge/meta").mkdir()
            (v / "knowledge/meta/p.md").write_text(
                "---\ntype: knowledge\nsources:\n  - raw/sources/ghost.md\n---\n",
                encoding="utf-8")
            (v / "raw/sources/orphan.md").write_text("# orphan\n", encoding="utf-8")
            issues = vault_sync.check_provenance(cfg)
            self.assertTrue(any(l == "FAIL" and "ghost" in m for l, m in issues))
            self.assertTrue(any(l == "WARN" and "orphan" in m for l, m in issues))


if __name__ == "__main__":
    unittest.main()
