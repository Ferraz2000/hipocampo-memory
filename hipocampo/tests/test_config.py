"""Tests for hipocampo.config — defaults, override merge, path/vocab helpers."""

import shutil
import tempfile
import unittest
from pathlib import Path

from hipocampo import config
from hipocampo.config import Config, DEFAULTS, deep_merge, load_config

_EXAMPLE = Path(__file__).resolve().parents[2] / "brain.config.example.toml"


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

    def test_valid_doc_sync_rule_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / config.CONFIG_FILENAME).write_text(
                '[[doc_sync]]\nname = "x"\n'
                'paths = ["src/**"]\ndocs = ["docs/x.md"]\n',
                encoding="utf-8",
            )
            cfg = load_config(start=root)
            self.assertEqual(cfg.doc_sync[0]["paths"], ["src/**"])

    def test_doc_sync_paths_as_string_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # `paths` as a bare string (a common TOML slip) must fail fast.
            (root / config.CONFIG_FILENAME).write_text(
                '[[doc_sync]]\nname = "x"\n'
                'paths = "src/**"\ndocs = ["docs/x.md"]\n',
                encoding="utf-8",
            )
            with self.assertRaises(config.ConfigError):
                load_config(start=root)

    def test_enforcement_defaults_and_override(self):
        from hipocampo.config import Config, DEFAULTS, deep_merge
        cfg = Config(DEFAULTS, Path("/repo"))
        # Default everywhere is block (backward compatible) including unknown points.
        self.assertEqual(cfg.enforcement_mode("pre_commit"), "block")
        self.assertEqual(cfg.enforcement_mode("ci"), "block")
        self.assertEqual(cfg.enforcement_mode("nonexistent"), "block")
        merged = deep_merge(DEFAULTS, {"enforcement": {"pre_commit": "warn", "pre_push": "off"}})
        warned = Config(merged, Path("/repo"))
        self.assertEqual(warned.enforcement_mode("pre_commit"), "warn")
        self.assertEqual(warned.enforcement_mode("pre_push"), "off")
        self.assertEqual(warned.enforcement_mode("ci"), "block")  # untouched

    def test_invalid_enforcement_mode_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / config.CONFIG_FILENAME).write_text(
                '[enforcement]\npre_commit = "nag"\n', encoding="utf-8")
            with self.assertRaises(config.ConfigError):
                load_config(start=root)

    def test_capture_auto_defaults_and_override(self):
        cfg = Config(DEFAULTS, Path("/repo"))
        self.assertEqual(cfg.capture_auto_mode, "inbox")   # backward-compatible default
        self.assertEqual(cfg.capture_auto_max, 7)
        merged = deep_merge(DEFAULTS, {"capture": {"auto": {"mode": "draft", "max_candidates": 3}}})
        drafted = Config(merged, Path("/repo"))
        self.assertEqual(drafted.capture_auto_mode, "draft")
        self.assertEqual(drafted.capture_auto_max, 3)

    def test_invalid_capture_auto_mode_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / config.CONFIG_FILENAME).write_text(
                '[capture.auto]\nmode = "automatic"\n', encoding="utf-8")
            with self.assertRaises(config.ConfigError):
                load_config(start=root)


class ExampleConfigTest(unittest.TestCase):
    """The shipped example must actually load when copied to brain.config.toml —
    its header promises 'Copy to brain.config.toml and edit'. TOML absorbs bare
    keys into the preceding [table], so key ordering matters; this guards it."""

    def test_example_loads_as_real_config(self):
        self.assertTrue(_EXAMPLE.is_file(), "brain.config.example.toml missing")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(_EXAMPLE, root / config.CONFIG_FILENAME)
            cfg = load_config(start=root)  # must NOT raise
            # Spot-check keys that were historically absorbed into the wrong table:
            self.assertEqual(cfg.areas, DEFAULTS["areas"])           # not under [dirs]
            self.assertEqual(cfg.validators, DEFAULTS["validators"])  # not under [search]
            self.assertEqual(cfg.doc_sync_escape_globs,              # not under [enforcement]
                             DEFAULTS["doc_sync_escape_globs"])
            self.assertEqual(cfg.enforcement_mode("ci"), "block")
            self.assertEqual(cfg.capture_auto_mode, "inbox")
            # Interview answers are now first-class config (no longer drift):
            self.assertEqual(cfg.project_mode, "existing")
            self.assertIs(cfg.team, False)

    def test_example_top_level_keys_match_defaults(self):
        import tomllib
        with open(_EXAMPLE, "rb") as fh:
            data = tomllib.load(fh)
        # Every example top-level key must be a real DEFAULTS key (catches a key
        # that silently nested into the wrong table, and a key documented in the
        # example but missing from DEFAULTS — the drift this guards against).
        self.assertTrue(set(data).issubset(set(DEFAULTS)),
                        f"unexpected top-level keys: {set(data) - set(DEFAULTS)}")


class InterviewAnswersTest(unittest.TestCase):
    """project_mode/team — interview answers recorded by /brain-init."""

    def test_defaults(self):
        cfg = Config(DEFAULTS, Path("/repo"))
        self.assertEqual(cfg.project_mode, "existing")
        self.assertIs(cfg.team, False)

    def test_overrides_apply(self):
        cfg = Config(deep_merge(DEFAULTS, {"project_mode": "greenfield", "team": True}),
                     Path("/repo"))
        self.assertEqual(cfg.project_mode, "greenfield")
        self.assertIs(cfg.team, True)

    def test_invalid_project_mode_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / config.CONFIG_FILENAME).write_text(
                'project_mode = "halfway"\n', encoding="utf-8")
            with self.assertRaises(config.ConfigError):
                load_config(start=root)

    def test_non_bool_team_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / config.CONFIG_FILENAME).write_text('team = "yes"\n', encoding="utf-8")
            with self.assertRaises(config.ConfigError):
                load_config(start=root)


if __name__ == "__main__":
    unittest.main()
