"""Tests for the capture-sweep and session-start hooks."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from hipocampo.config import Config, DEFAULTS, deep_merge
import os

from hipocampo.hooks import capture_sweep as cs
from hipocampo.hooks import ensure_githooks as eg
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

    def test_redact_scrubs_secret_shapes(self):
        self.assertIn("[REDACTED]", cs.redact("the password is hunter2-S3cret!"))
        self.assertIn("[REDACTED]", cs.redact("token=abcd1234 in config"))
        self.assertIn("[REDACTED]", cs.redact("key AKIA1234567890ABCDEF here"))
        self.assertIn("[REDACTED]", cs.redact("AWS_SECRET_ACCESS_KEY=AKIA1234567890ABCDEF"))
        self.assertEqual(cs.redact("nothing secret here"), "nothing secret here")

    def test_redact_scrubs_unlabeled_high_entropy_tokens(self):
        # Tokens pasted without a labeling keyword — the labeled rule misses these.
        self.assertIn("[REDACTED]", cs.redact("ghp_16C7e42F292c6912E7710c838347Ae178B4a01"))
        self.assertIn("[REDACTED]", cs.redact("sk-proj-abc123def456ghi789jkl012mnop"))
        self.assertIn("[REDACTED]", cs.redact("xoxb-12345-abcdefGHIJKLmnop"))
        self.assertIn("[REDACTED]", cs.redact(
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NSJ9.SflKxwRJSMeKKF2QT4fwpM"))
        # No false positive on ordinary prose.
        self.assertEqual(cs.redact("we shipped the feature today"),
                         "we shipped the feature today")

    def test_filter_new_drops_captured_and_pending(self):
        urls = {"https://example.com/a", "https://example.com/b"}
        triggers = [("decided", "we decided to ship"), ("trade-off", "the trade-off is X")]
        captured = {"https://example.com/a"}
        inbox_blob = "we decided to ship"
        new_urls, new_triggers = cs.filter_new(urls, triggers, captured, inbox_blob)
        self.assertEqual(new_urls, {"https://example.com/b"})
        self.assertEqual([t for t, _ in new_triggers], ["trade-off"])


class EnsureGithooksTest(unittest.TestCase):
    """Regression: the SessionStart hook must run without raising (it once shipped
    a missing `import os` that crashed on every invocation)."""

    def _run_in(self, path):
        cwd = os.getcwd()
        os.chdir(path)
        try:
            return eg.main()
        finally:
            os.chdir(cwd)

    def test_main_is_noop_without_githooks_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._run_in(tmp), 0)  # no .githooks → silent no-op, no crash

    def test_main_sets_hookspath_when_githooks_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            except (FileNotFoundError, subprocess.CalledProcessError):
                self.skipTest("git not available")
            (Path(tmp) / ".githooks").mkdir()
            self.assertEqual(self._run_in(tmp), 0)
            got = subprocess.run(["git", "config", "core.hooksPath"], cwd=tmp,
                                 capture_output=True, text=True).stdout.strip()
            self.assertEqual(got, ".githooks")


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
            triggers, urls, captured = cs.scan_transcript(path, self.cfg)
            found = {t.lower() for t, _ in triggers}
            self.assertIn("decided", found)
            self.assertIn("anti-pattern", found)
            self.assertIn("https://example.com/x", urls)
            self.assertFalse(captured)

    def test_user_trigger_not_fired_from_agent_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _transcript(tmp, [
                {"role": "assistant", "content": "I decided to refactor"},  # agent says "decided"
            ])
            triggers, _urls, _r = cs.scan_transcript(path, self.cfg)
            self.assertEqual(triggers, [])  # "decided" is a user-only trigger

    def test_capture_invocation_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _transcript(tmp, [{"role": "user", "content": "/capture this decision"}])
            _t, _u, captured = cs.scan_transcript(path, self.cfg)
            self.assertTrue(captured)

    def test_gemini_parts_shape_is_parsed(self):
        # Gemini transcript events carry text under `parts`, role under `model`.
        with tempfile.TemporaryDirectory() as tmp:
            path = _transcript(tmp, [
                {"role": "user", "parts": [{"text": "we decided to use Redis"}]},
                {"role": "model", "parts": [{"text": "noted, that is canonical now"}]},
            ])
            triggers, _urls, _c = cs.scan_transcript(path, self.cfg)
            found = {t.lower() for t, _ in triggers}
            self.assertIn("decided", found)      # user-side trigger
            self.assertIn("canonical", found)    # agent-side trigger via role=model

    def test_codex_message_wrapped_shape_is_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _transcript(tmp, [
                {"message": {"role": "user", "content": "the rule of thumb is X"}},
            ])
            triggers, _urls, _c = cs.scan_transcript(path, self.cfg)
            self.assertIn("rule of thumb", {t.lower() for t, _ in triggers})


class ExtractHelperTest(unittest.TestCase):
    def test_content_text_flattens_shapes(self):
        self.assertEqual(cs._content_text("hi"), "hi")
        self.assertEqual(cs._content_text([{"text": "a"}, {"text": "b"}]), "a b")
        self.assertEqual(cs._content_text(["a", "b"]), "a b")
        self.assertEqual(cs._content_text(None), "")
        # Regression: a nested list (Claude tool_result whose `content` is itself
        # a list of blocks) must flatten, not raise "expected str, list found".
        self.assertEqual(
            cs._content_text(
                [{"type": "tool_result", "content": [{"type": "text", "text": "nested ok"}]}]
            ),
            "nested ok",
        )
        self.assertEqual(cs._content_text({"type": "text", "text": "dict direct"}), "dict direct")

    def test_extract_normalizes_roles(self):
        self.assertEqual(cs._extract({"role": "human", "content": "x"})[1], "user")
        self.assertEqual(cs._extract({"role": "model", "parts": [{"text": "y"}]})[1], "assistant")
        self.assertEqual(cs._extract({"type": "assistant", "content": "z"})[1], "assistant")


class PendingCaptureTest(unittest.TestCase):
    """Phase 12 draft-mode staging (disposable cache, human-gated review)."""

    def _draft_cfg(self, root):
        return Config(deep_merge(DEFAULTS, {"capture": {"auto": {"mode": "draft"}}}), root)

    def test_render_pending_block_caps_and_uses_checkboxes(self):
        triggers = [("decided", f"snippet {i}") for i in range(20)]
        block = cs._render_pending_block("2026-06-17", "abcd1234", triggers, set(),
                                         max_candidates=3)
        self.assertEqual(block.count("- [ ]"), 3)        # capped
        self.assertIn("## Session abcd1234", block)

    def test_pending_header_points_at_review_and_persona(self):
        h = cs._pending_header(persona_file="docs/brain/USER.md")
        self.assertIn("/capture --review", h)
        self.assertIn("docs/brain/USER.md", h)
        self.assertIn(".brain-cache", h)
        self.assertIn("transcript", h)   # tells the agent to read the real session

    def test_pending_block_records_transcript_pointer(self):
        block = cs._render_pending_block("2026-06-17", "abcd1234", [("decided", "x")], set(),
                                         transcript="/tmp/session-abcd.jsonl")
        self.assertIn("> transcript: /tmp/session-abcd.jsonl", block)
        # absent when not provided (degrades to snippet-only review)
        self.assertNotIn("transcript:", cs._render_pending_block(
            "2026-06-17", "abcd1234", [("decided", "x")], set()))

    def test_write_pending_lands_in_cache_not_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._draft_cfg(Path(tmp))
            staging = cfg.cache_dir / "pending-capture.md"
            cs._write_pending(staging, "2026-06-17", "abcd1234", "sid",
                              [("decided", "we decided X")], {"https://e.com/x"}, cfg)
            self.assertTrue(staging.exists())
            self.assertFalse(cfg.inbox_dir.exists())     # vault untouched
            txt = staging.read_text(encoding="utf-8")
            self.assertIn("- [ ]", txt)
            self.assertIn("source: https://e.com/x", txt)

    def test_write_pending_dedups_same_session_appends_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._draft_cfg(Path(tmp))
            staging = cfg.cache_dir / "pending-capture.md"
            cs._write_pending(staging, "2026-06-17", "aaaa", "s1", [("decided", "x")], set(), cfg)
            cs._write_pending(staging, "2026-06-17", "aaaa", "s1", [("decided", "x")], set(), cfg)
            txt = staging.read_text(encoding="utf-8")
            self.assertEqual(txt.lower().count("## session aaaa"), 1)   # not duplicated
            cs._write_pending(staging, "2026-06-17", "bbbb", "s2", [("trade-off", "y")], set(), cfg)
            self.assertIn("## Session bbbb", staging.read_text(encoding="utf-8"))

    def test_draft_mode_max_default_is_seven(self):
        cfg = self._draft_cfg(Path("/repo"))
        self.assertEqual(cfg.capture_auto_mode, "draft")
        self.assertEqual(cfg.capture_auto_max, 7)


class SessionStartTest(unittest.TestCase):
    def test_base_falls_back_to_master_when_main_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", "-b", "master"], cwd=root)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=root)
            subprocess.run(["git", "config", "user.name", "t"], cwd=root)
            subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=root)
            (root / "a.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=root)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=root)
            subprocess.run(["git", "checkout", "-q", "-b", "feature"], cwd=root)
            (root / "b.txt").write_text("y", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=root)
            subprocess.run(["git", "commit", "-qm", "work"], cwd=root)
            cfg = Config(DEFAULTS, root)  # base_branch=main, repo only has master
            out = ss.build_briefing(cfg)
            self.assertIn("ahead of master", out)
            self.assertNotIn("ahead of main", out)

    def test_single_branch_repo_reports_no_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", "-b", "master"], cwd=root)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=root)
            subprocess.run(["git", "config", "user.name", "t"], cwd=root)
            subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=root)
            (root / "a.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=root)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=root)
            cfg = Config(DEFAULTS, root)
            out = ss.build_briefing(cfg)
            self.assertIn("No base branch resolved", out)

    def test_briefing_on_real_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=root)
            subprocess.run(["git", "config", "user.name", "t"], cwd=root)
            subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=root)
            (root / "a.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=root)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=root)
            cfg = Config(DEFAULTS, root)
            out = ss.build_briefing(cfg)
            self.assertIn("Work in progress", out)
            self.assertLessEqual(len(out), 8000)

    def test_json_envelope_wraps_additional_context(self):
        env = ss._emit("BRIEFING TEXT", "json")
        obj = json.loads(env)
        self.assertEqual(obj["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertEqual(obj["hookSpecificOutput"]["additionalContext"], "BRIEFING TEXT")

    def test_main_format_json_emits_valid_json_envelope(self):
        # Guards the CLI wiring: --format json must reach argparse and produce JSON
        # on stdout (not raw markdown), which is what Codex/Gemini parse.
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = ss.main(["--format", "json"])
        self.assertEqual(rc, 0)
        obj = json.loads(buf.getvalue())  # raises if it emitted plain text
        self.assertEqual(obj["hookSpecificOutput"]["hookEventName"], "SessionStart")

    def test_main_default_format_is_plain_text(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ss.main([])
        self.assertTrue(buf.getvalue().lstrip().startswith("#"))

    def test_plain_format_is_raw_text(self):
        self.assertEqual(ss._emit("BRIEFING TEXT", "plain"), "BRIEFING TEXT")

    def test_briefing_surfaces_pending_capture_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = Config(DEFAULTS, root)
            cfg.cache_dir.mkdir(parents=True, exist_ok=True)
            (cfg.cache_dir / "pending-capture.md").write_text("# Pending", encoding="utf-8")
            out = ss.build_briefing(cfg)
            self.assertIn("/capture --review", out)
            self.assertIn(".brain-cache/pending-capture.md", out)


class PersonaConfigTest(unittest.TestCase):
    def test_render_sweep_uses_configured_persona_file(self):
        out = cs._render_sweep("2026-06-16", "abcd1234", "sid", "capture-sweep",
                               [("decided", "we decided X")], set(),
                               persona_file="docs/brain/USER.md")
        self.assertIn("docs/brain/USER.md", out)
        self.assertNotIn(".claude/rules/USER.md", out)

    def test_persona_file_default_and_override(self):
        self.assertEqual(Config(DEFAULTS, Path("/repo")).persona_file, ".claude/rules/USER.md")
        from hipocampo.config import deep_merge
        merged = deep_merge(DEFAULTS, {"memory": {"persona_file": "AGENTS/USER.md"}})
        self.assertEqual(Config(merged, Path("/repo")).persona_file, "AGENTS/USER.md")


if __name__ == "__main__":
    unittest.main()
