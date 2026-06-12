"""Tests for the capture-sweep and session-start hooks."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from hipocampo.config import Config, DEFAULTS
from hipocampo.hooks import capture_sweep as cs
from hipocampo.hooks import session_start as ss


def _transcript(tmp, events):
    p = Path(tmp) / "transcript.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    return str(p)


class PureHelpersTest(unittest.TestCase):
    def test_is_external(self):
        hosts = ["localhost", "127.0.0.1"]
        self.assertTrue(cs.is_external("https://example.com/x", hosts))
        self.assertFalse(cs.is_external("http://localhost:5000/y", hosts))

    def test_filter_new_drops_captured_and_pending(self):
        urls = {"https://example.com/a", "https://example.com/b"}
        triggers = [("decided", "we decided to ship"), ("trade-off", "the trade-off is X")]
        captured = {"https://example.com/a"}
        inbox_blob = "we decided to ship"
        new_urls, new_triggers = cs.filter_new(urls, triggers, captured, inbox_blob)
        self.assertEqual(new_urls, {"https://example.com/b"})
        self.assertEqual([t for t, _ in new_triggers], ["trade-off"])


class ScanTranscriptTest(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(DEFAULTS, Path("/repo"))

    def test_detects_user_and_agent_triggers_and_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _transcript(tmp, [
                {"role": "user", "content": "I decided we use Postgres"},
                {"role": "assistant", "content": [{"text": "that is an anti-pattern"}]},
                {"role": "assistant", "content": "ref https://example.com/x"},
            ])
            triggers, urls, registra = cs.scan_transcript(path, self.cfg)
            found = {t.lower() for t, _ in triggers}
            self.assertIn("decided", found)
            self.assertIn("anti-pattern", found)
            self.assertIn("https://example.com/x", urls)
            self.assertFalse(registra)

    def test_user_trigger_not_fired_from_agent_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _transcript(tmp, [
                {"role": "assistant", "content": "I decided to refactor"},  # agent says "decided"
            ])
            triggers, _urls, _r = cs.scan_transcript(path, self.cfg)
            self.assertEqual(triggers, [])  # "decided" is a user-only trigger

    def test_registra_invocation_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _transcript(tmp, [{"role": "user", "content": "/registra this decision"}])
            _t, _u, registra = cs.scan_transcript(path, self.cfg)
            self.assertTrue(registra)


class SessionStartTest(unittest.TestCase):
    def test_briefing_on_real_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=root)
            subprocess.run(["git", "config", "user.name", "t"], cwd=root)
            (root / "a.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=root)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=root)
            cfg = Config(DEFAULTS, root)
            out = ss.build_briefing(cfg)
            self.assertIn("Work in progress", out)
            self.assertLessEqual(len(out), 8000)


if __name__ == "__main__":
    unittest.main()
