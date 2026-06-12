"""Tests for hipocampo.config — defaults, override merge, path/vocab helpers."""

import tempfile
import unittest
from pathlib import Path

from hipocampo import config
from hipocampo.config import Config, DEFAULTS, deep_merge, load_config


class DeepMergeTest(unittest.TestCase):
    def test_overrides_scalar_keeps_siblings(self):
        merged = deep_merge({"a": 1, "b": {"x": 1, "y": 2}}, {"b": {"y": 9}})
        self.assertEqual(merged, {"a": 1, "b": {"x": 1, "y": 9}})

    def test_does_not_mutate_base(self):
        base = {"b": {"x": 1}}
        deep_merge(base, {"b": {"x": 2}})
        self.assertEqual(base, {"b": {"x": 1}})


class DefaultsConfigTest(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(DEFAULTS, Path("/repo"))

    def test_vault_and_dir_paths(self):
        self.assertEqual(self.cfg.vault_root, Path("/repo/docs/brain"))
        self.assertEqual(self.cfg.inbox_dir, Path("/repo/docs/brain/knowledge/_inbox"))
        self.assertEqual(self.cfg.raw_sources_dir, Path("/repo/docs/brain/raw/sources"))

    def test_cache_is_repo_relative_not_vault_relative(self):
        self.assertEqual(self.cfg.cache_dir, Path("/repo/.brain-cache"))

    def test_vocabulary_helpers(self):
        self.assertIn("triage", self.cfg.statuses)
        self.assertIn("meta", self.cfg.areas)
        self.assertEqual(self.cfg.inbox_decay_days, 30)
        self.assertEqual(self.cfg.inbox_sweep_type, "capture-sweep")


class LoadConfigTest(unittest.TestCase):
    def test_missing_file_uses_defaults_and_git_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            sub = root / "a" / "b"
            sub.mkdir(parents=True)
            cfg = load_config(start=sub)
            self.assertIsNone(cfg.config_path)
            self.assertEqual(cfg.repo_root, root)
            self.assertEqual(cfg.vault_root, root / "docs/brain")

    def test_file_overrides_merge_over_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / config.CONFIG_FILENAME).write_text(
                'vault_root = "docs/obsidian"\n'
                '[inbox]\n'
                'decay_days = 7\n',
                encoding="utf-8",
            )
            cfg = load_config(start=root)
            # overridden
            self.assertEqual(cfg.vault_root, root / "docs/obsidian")
            self.assertEqual(cfg.inbox_decay_days, 7)
            # untouched default survives the partial [inbox] override
            self.assertEqual(cfg.inbox_sweep_type, "capture-sweep")

    def test_invalid_toml_raises_configerror(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / config.CONFIG_FILENAME).write_text("this is = = not valid", encoding="utf-8")
            with self.assertRaises(config.ConfigError):
                load_config(start=root)

    def test_local_override_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / config.CONFIG_FILENAME).write_text(
                '[inbox]\ndecay_days = 30\n', encoding="utf-8")
            (root / config.LOCAL_OVERRIDE_FILENAME).write_text(
                '[inbox]\ndecay_days = 1\n', encoding="utf-8")
            cfg = load_config(start=root)
            self.assertEqual(cfg.inbox_decay_days, 1)


if __name__ == "__main__":
    unittest.main()
