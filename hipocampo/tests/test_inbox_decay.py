"""Tests for hipocampo.inbox_decay — only stale ephemeral sweeps are touched."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from hipocampo.config import Config, DEFAULTS
from hipocampo.inbox_decay import decay, find_stale

TODAY = date(2026, 6, 12)


def _sweep(created, *, type="capture-sweep", status="triage", pinned=None):
    fm = [f"type: {type}", f"status: {status}", f"created: {created}"]
    if pinned is not None:
        fm.append(f"pinned: {pinned}")
    return "---\n" + "\n".join(fm) + "\n---\n\nbody\n"


class InboxDecayTest(unittest.TestCase):
    def _vault(self, tmp):
        root = Path(tmp)
        inbox = root / "docs/brain/knowledge/_inbox"
        inbox.mkdir(parents=True)
        cfg = Config(DEFAULTS, root)
        return cfg, inbox

    def test_only_stale_untriaged_unpinned_sweeps_are_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, inbox = self._vault(tmp)
            (inbox / "old.md").write_text(_sweep("2026-04-01"), encoding="utf-8")        # 72d -> stale
            (inbox / "fresh.md").write_text(_sweep("2026-06-10"), encoding="utf-8")      # 2d  -> keep
            (inbox / "pinned.md").write_text(_sweep("2026-04-01", pinned="true"), encoding="utf-8")
            (inbox / "triaged.md").write_text(_sweep("2026-04-01", status="active"), encoding="utf-8")
            (inbox / "human.md").write_text(_sweep("2026-04-01", type="knowledge"), encoding="utf-8")

            stale = find_stale(cfg.inbox_dir, cfg.inbox_sweep_type, days=30, today=TODAY)
            names = {Path(p).name for p, _ in stale}
            self.assertEqual(names, {"old.md"})

    def test_dry_run_does_not_delete_apply_does(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, inbox = self._vault(tmp)
            target = inbox / "old.md"
            target.write_text(_sweep("2026-04-01"), encoding="utf-8")

            decay(cfg=cfg, days=30, apply=False, today=TODAY)
            self.assertTrue(target.exists())

            decay(cfg=cfg, days=30, apply=True, today=TODAY)
            self.assertFalse(target.exists())

    def test_unparseable_date_is_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, inbox = self._vault(tmp)
            (inbox / "bad.md").write_text(_sweep("not-a-date"), encoding="utf-8")
            stale = find_stale(cfg.inbox_dir, cfg.inbox_sweep_type, days=30, today=TODAY)
            self.assertEqual(stale, [])

    def test_missing_inbox_is_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(DEFAULTS, Path(tmp))  # no inbox dir created
            self.assertEqual(decay(cfg=cfg, today=TODAY), [])


if __name__ == "__main__":
    unittest.main()
