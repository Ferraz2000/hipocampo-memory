"""Tests for the scaffolded vault templates (templates/vault/<lang>/).

Guards two things: the locales stay in parity, and a freshly-scaffolded vault is
valid (passes the vault-sync validator) out of the box.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from hipocampo.config import Config, DEFAULTS
from hipocampo.validators import vault_sync

REPO_ROOT = Path(__file__).resolve().parents[2]
VAULT_TEMPLATES = REPO_ROOT / "templates" / "vault"
HOOK_TEMPLATES = REPO_ROOT / "templates" / "hooks"
LOCALES = ["en", "pt-BR"]


def _rel_files(root):
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


class TemplatesTest(unittest.TestCase):
    def test_locales_have_identical_file_sets(self):
        sets = {loc: _rel_files(VAULT_TEMPLATES / loc) for loc in LOCALES}
        self.assertEqual(sets["en"], sets["pt-BR"],
                         "EN and pt-BR locale file sets diverged")

    def test_each_locale_has_the_core_limiters(self):
        required = {"README.md", "capture.md", "context-budget.md", "log.md",
                    "knowledge/index.md"}
        for loc in LOCALES:
            present = _rel_files(VAULT_TEMPLATES / loc)
            self.assertTrue(required.issubset(present), f"{loc} missing core limiters")

    def test_scaffolded_vault_passes_vault_sync(self):
        for loc in LOCALES:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                vault = root / "docs" / "brain"
                shutil.copytree(VAULT_TEMPLATES / loc, vault)
                # Render the date placeholder the generator would fill in.
                for md in vault.rglob("*.md"):
                    md.write_text(md.read_text(encoding="utf-8").replace("{{DATE}}", "2026-06-12").replace("{{CAPTURE_LEVEL}}", "balanced"),
                                  encoding="utf-8")
                cfg = Config(DEFAULTS, root)
                results = (vault_sync.check_knowledge_index(cfg)
                           + vault_sync.check_status_area(cfg)
                           + vault_sync.check_provenance(cfg))
                fails = [m for level, m in results if level == "FAIL"]
                self.assertEqual(fails, [], f"{loc}: fresh vault should have no FAILs")


class HookTemplatesTest(unittest.TestCase):
    """The per-agent hook wiring (Codex/Gemini) must be valid and self-consistent."""

    CASES = {
        "codex/hooks.json": {"SessionStart", "Stop"},
        "gemini/settings.hooks.json": {"SessionStart", "SessionEnd"},
    }

    def _commands(self, hooks_obj):
        for entries in hooks_obj.values():
            for entry in entries:
                for h in entry.get("hooks", []):
                    yield h.get("command", "")

    def test_templates_are_valid_json_with_expected_events(self):
        for rel, events in self.CASES.items():
            data = json.loads((HOOK_TEMPLATES / rel).read_text(encoding="utf-8"))
            self.assertEqual(set(data["hooks"]), events, f"{rel}: unexpected events")

    def test_templates_wire_the_hipocampo_modules(self):
        for rel in self.CASES:
            data = json.loads((HOOK_TEMPLATES / rel).read_text(encoding="utf-8"))
            cmds = " ".join(self._commands(data["hooks"]))
            # Session start injects context as JSON; session end runs the sweep.
            self.assertIn("hipocampo.hooks.session_start --format json", cmds)
            self.assertIn("hipocampo.hooks.capture_sweep", cmds)
            self.assertIn("hipocampo.hooks.ensure_githooks", cmds)


if __name__ == "__main__":
    unittest.main()
