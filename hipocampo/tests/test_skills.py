"""Guards the plugin packaging: valid manifests and well-formed skills."""

import json
import unittest
from pathlib import Path

from hipocampo.frontmatter import parse_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "plugin" / "skills"
EXPECTED_SKILLS = {
    "brain-init", "brain-router-init", "brain-scripts-init", "brain-update",
    "capture", "search", "audit", "discovery", "spec",
    "challenge", "discover-standards", "garden", "archive-closed",
    "execute-insight", "from-roadmap", "implement", "promote",
    "weekly", "postmortem", "low-token",
}


class ManifestTest(unittest.TestCase):
    def test_manifests_are_valid_json(self):
        for rel in (".claude-plugin/plugin.json",
                    ".claude-plugin/marketplace.json",
                    "plugin/hooks/hooks.json"):
            with self.subTest(rel=rel):
                json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))

    def test_plugin_points_at_skills_and_hooks(self):
        manifest = json.loads((REPO_ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "hipocampo")
        self.assertTrue((REPO_ROOT / manifest["skills"]).is_dir())
        self.assertTrue((REPO_ROOT / manifest["hooks"]).is_file())

    def test_hooks_reference_the_python_hooks(self):
        hooks = json.loads((REPO_ROOT / "plugin/hooks/hooks.json").read_text(encoding="utf-8"))
        commands = [h["command"] for grp in hooks["hooks"].values() for entry in grp for h in entry["hooks"]]
        joined = " ".join(commands)
        self.assertIn("hipocampo.hooks.session_start", joined)
        self.assertIn("hipocampo.hooks.capture_sweep", joined)


class SkillsTest(unittest.TestCase):
    def test_all_expected_skills_present(self):
        present = {p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md")}
        self.assertEqual(present, EXPECTED_SKILLS)

    def test_each_skill_has_name_and_description(self):
        for skill in EXPECTED_SKILLS:
            fields, body = parse_frontmatter((SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8"))
            self.assertEqual(fields.get("name"), skill, f"{skill}: name must match dir")
            self.assertTrue(fields.get("description"), f"{skill}: description required")
            self.assertTrue(body.strip(), f"{skill}: body required")


if __name__ == "__main__":
    unittest.main()
