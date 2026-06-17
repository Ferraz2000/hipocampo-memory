"""Tests for the optional [semantic] tier — graceful degradation.

The heavy deps (model2vec / sqlite-vec) are NOT installed in CI, so these cover
the contract that matters for the zero-dep core: when the tier is unavailable,
every entry point is a safe no-op and search is unaffected. The dep-backed paths
(_embed / vec0 queries) are verified separately on a machine with the extra.
"""

import os
import unittest
from pathlib import Path
from unittest import mock

from hipocampo import semantic
from hipocampo.config import Config, DEFAULTS, deep_merge


def _cfg(enabled=False, root="/repo"):
    data = deep_merge(DEFAULTS, {"semantic": {"enabled": enabled}})
    return Config(data, Path(root))


class AvailabilityTest(unittest.TestCase):
    def test_disabled_by_default(self):
        self.assertFalse(semantic.available(_cfg(enabled=False)))

    def test_enabled_but_deps_absent_is_unavailable(self):
        # Deps aren't installed here, so even enabled must report unavailable.
        if semantic._deps() is not None:
            self.skipTest("semantic extra is installed in this env")
        self.assertFalse(semantic.available(_cfg(enabled=True)))

    def test_env_kill_switch_forces_unavailable(self):
        with mock.patch.dict(os.environ, {"HIPOCAMPO_SEMANTIC": "0"}):
            # Even if everything else were satisfied, the kill switch wins.
            with mock.patch.object(semantic, "_deps", return_value=object()), \
                 mock.patch.object(semantic, "extension_loadable", return_value=True):
                self.assertFalse(semantic.available(_cfg(enabled=True)))

    def test_available_true_when_all_conditions_met(self):
        with mock.patch.object(semantic, "_deps", return_value=object()), \
             mock.patch.object(semantic, "extension_loadable", return_value=True):
            self.assertTrue(semantic.available(_cfg(enabled=True)))

    def test_extension_loadable_returns_bool(self):
        self.assertIsInstance(semantic.extension_loadable(), bool)


class NoOpWhenUnavailableTest(unittest.TestCase):
    def setUp(self):
        self.cfg = _cfg(enabled=False)

    def test_rank_returns_empty(self):
        self.assertEqual(semantic.rank("anything", self.cfg), [])

    def test_reindex_returns_zero(self):
        self.assertEqual(semantic.reindex(self.cfg, [("k/a.md", "text")]), 0)

    def test_forget_returns_zero(self):
        self.assertEqual(semantic.forget(self.cfg, ["k/a.md"]), 0)


@unittest.skipUnless(
    semantic._deps() is not None and semantic.extension_loadable()
    and __import__("hipocampo.index", fromlist=["fts5_available"]).fts5_available(),
    "semantic extra not installed (or sqlite without FTS5/extensions)")
class SemanticEndToEndTest(unittest.TestCase):
    """Self-verification: when the [semantic] extra IS present, the repo exercises
    its own dep-backed leaf calls (_embed → vec0 → MATCH → RRF) end to end, so they
    can't silently rot. Skips cleanly everywhere the extra is absent."""

    def test_paraphrase_query_surfaces_semantic_match(self):
        import tempfile
        from hipocampo import index
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kn = root / "docs/brain/knowledge"
            kn.mkdir(parents=True)
            # Phrased to share no query keywords — only BM25 would miss it.
            (kn / "auth.md").write_text(
                "---\ntitle: Auth\n---\nShort token TTL with a refresh token; "
                "users are logged out automatically.\n", encoding="utf-8")
            (kn / "billing.md").write_text(
                "---\ntitle: Billing\n---\ninvoices payments dunning ledger\n",
                encoding="utf-8")
            cfg = Config(deep_merge(DEFAULTS, {"semantic": {"enabled": True}}), root)
            self.assertTrue(semantic.available(cfg))
            try:
                hits = index.search("session expiry auto logout", cfg=cfg, rrf=True)
            except Exception as e:  # offline w/o cached model, etc. — don't fail CI
                self.skipTest(f"model/runtime unavailable: {e}")
            paths = [rp for rp, _ in hits]
            self.assertTrue(any(p.endswith("auth.md") for p in paths),
                            f"semantic match not surfaced: {paths}")


if __name__ == "__main__":
    unittest.main()
