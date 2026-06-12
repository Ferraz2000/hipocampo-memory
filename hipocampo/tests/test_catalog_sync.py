"""Tests for the catalog_sync validator."""

import tempfile
import unittest
from pathlib import Path

from hipocampo.validators.catalog_sync import (catalog_table_skills,
                                               discover_skill_bundles,
                                               required_files_violations,
                                               skill_catalog_violations)


def _bundle(root, name, fm_name=None, description=True):
    d = root / name
    d.mkdir(parents=True)
    fm = [f"name: {fm_name if fm_name is not None else name}"]
    if description:
        fm.append("description: does things")
    (d / "SKILL.md").write_text("---\n" + "\n".join(fm) + "\n---\nbody\n", encoding="utf-8")


class CatalogSyncTest(unittest.TestCase):
    def test_good_bundle_listed_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _bundle(root, "alpha")
            bundles = discover_skill_bundles(str(root))
            self.assertEqual(skill_catalog_violations(bundles, "| `alpha` | x |"), [])

    def test_name_mismatch_missing_description_unlisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _bundle(root, "alpha", fm_name="beta", description=False)
            issues = skill_catalog_violations(discover_skill_bundles(str(root)), "no mention")
            msgs = " ".join(m for _, m in issues)
            self.assertIn("!= directory", msgs)
            self.assertIn("missing description", msgs)
            self.assertIn("not listed", msgs)

    def test_catalog_table_parse_and_orphans(self):
        ids = catalog_table_skills("| `alpha` | x |\n| `gone` | y |\nprose `ignored`")
        self.assertEqual(ids, ["alpha", "gone"])

    def test_required_files_existence_and_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("\n".join(["l"] * 200), encoding="utf-8")
            (root / "sub").mkdir()
            (root / "sub/AGENTS.md").write_text("\n".join(["l"] * 100), encoding="utf-8")
            issues = required_files_violations(
                str(root), ["AGENTS.md", "sub/AGENTS.md", "ghost/AGENTS.md"],
                max_lines=80, skip_cap_for="AGENTS.md")
            msgs = " ".join(issues)
            self.assertIn("ghost/AGENTS.md", msgs)          # missing
            self.assertIn("sub/AGENTS.md: 100 lines", msgs)  # over cap
            self.assertNotIn("AGENTS.md: 200", msgs)         # router cap skipped


if __name__ == "__main__":
    unittest.main()
