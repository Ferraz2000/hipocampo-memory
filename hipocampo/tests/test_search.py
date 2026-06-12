"""Tests for hipocampo.search — pure BM25 path, status filtering, helpers."""

import tempfile
import unittest
from pathlib import Path

from hipocampo.config import Config, DEFAULTS
from hipocampo.search import run_search, status_of, tokenize, title_of


def _note(status=None, title=None, body=""):
    fm = []
    if title is not None:
        fm.append(f"title: {title}")
    if status is not None:
        fm.append(f"status: {status}")
    head = ("---\n" + "\n".join(fm) + "\n---\n") if fm else ""
    return head + body + "\n"


class HelpersTest(unittest.TestCase):
    def test_status_of_reads_only_frontmatter(self):
        self.assertEqual(status_of(_note(status="closed", body="status: active in prose")), "closed")
        self.assertEqual(status_of("no frontmatter here"), "")

    def test_tokenize_strips_diacritics_and_case(self):
        self.assertEqual(tokenize("Migração RÁPIDA"), ["migracao", "rapida"])

    def test_title_prefers_frontmatter_then_h1(self):
        self.assertEqual(title_of(_note(title="From FM"), "fb"), "From FM")
        self.assertEqual(title_of("# An H1 Heading\n\nbody", "fb"), "An H1 Heading")


class RunSearchTest(unittest.TestCase):
    def _vault(self, tmp):
        root = Path(tmp)
        kn = root / "docs/brain/knowledge"
        kn.mkdir(parents=True)
        return Config(DEFAULTS, root), kn

    def test_ranks_relevant_note_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, kn = self._vault(tmp)
            (kn / "onboarding.md").write_text(
                _note(title="Store onboarding", body="onboarding store flow onboarding store"),
                encoding="utf-8")
            (kn / "billing.md").write_text(
                _note(title="Billing", body="invoices and payments"), encoding="utf-8")
            results, _ = run_search("onboarding store", cfg=cfg, no_index=True)
            self.assertTrue(results)
            self.assertTrue(results[0][0].endswith("onboarding.md"))

    def test_terminal_status_hidden_by_default_shown_with_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, kn = self._vault(tmp)
            (kn / "dead.md").write_text(
                _note(status="closed", body="onboarding onboarding"), encoding="utf-8")
            hidden_only, hidden = run_search("onboarding", cfg=cfg, no_index=True)
            self.assertEqual(hidden_only, [])
            self.assertEqual(hidden, 1)
            shown, _ = run_search("onboarding", cfg=cfg, no_index=True, all_statuses=True)
            self.assertEqual(len(shown), 1)

    def test_index_md_excluded_from_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, kn = self._vault(tmp)
            (kn / "index.md").write_text(_note(title="Index", body="onboarding onboarding"), encoding="utf-8")
            (kn / "real.md").write_text(_note(title="Real", body="onboarding flow"), encoding="utf-8")
            results, _ = run_search("onboarding", cfg=cfg, no_index=True)
            paths = [r[0].replace("\\", "/") for r in results]
            self.assertTrue(paths)
            self.assertFalse(any(p.endswith("knowledge/index.md") for p in paths))

    def test_empty_query_returns_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = self._vault(tmp)
            self.assertEqual(run_search("!!!", cfg=cfg, no_index=True), ([], 0))


if __name__ == "__main__":
    unittest.main()
