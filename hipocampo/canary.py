#!/usr/bin/env python3
"""Canary: adversarial self-test of the governance gates, against THIS repo's
real ``brain.config.toml``.

Validators are production code for the workflow — they need adversarial checks
too, in the consumer repo (proves the vendored kit + the config wiring still
bite). Each scenario builds a throwaway fixture (temp dir or in-memory lists —
the real tree is never touched) and asserts the gate FAILS when it must and
PASSES when it must.

Scenarios (skipped when the config doesn't define the ingredient):
  1. doc-sync: a file matching the first ``[[doc_sync]]`` rule, without its doc → must FAIL.
  2. doc-sync: same file + one of the rule's docs → must PASS.
  3. doc-sync: same file + a file matching an escape glob → must PASS.
  4. vault_sync: insight with off-vocabulary status → must FAIL.
  5. vault_sync: knowledge page missing from the index → must FAIL.
  6. vault_sync: knowledge page citing a non-existent source → must FAIL.
  7. doc_links: broken relative markdown link → must FAIL.

Usage:  python -m hipocampo.canary        (exit 0 = all gates bite)
"""

import sys
import tempfile
from pathlib import Path

from . import config as _config
from .config import Config
from .validators import doc_links as _dl
from .validators import feature_doc_sync as _fds
from .validators import vault_sync as _vs


def _synth_path(glob):
    """A concrete path that matches the glob (for doc-sync rule probing)."""
    out = []
    for part in glob.split("/"):
        if part == "**":
            out.append("canary")
        elif "*" in part:
            out.append(part.replace("*", "canary"))
        else:
            out.append(part)
    if not out[-1].count("."):
        out.append("canary.txt")
    return "/".join(out)


def _scenarios(cfg):
    yield_skip = lambda name: (name, None, None)

    # --- doc-sync (in-memory changed-file lists; pure functions)
    if cfg.doc_sync:
        rule = cfg.doc_sync[0]
        probe = _synth_path(rule["paths"][0])
        yield ("doc-sync: sensitive file without doc MUST FAIL",
               lambda: bool(_fds.failures([probe], cfg)), True)
        doc = rule.get("docs", [None])[0]
        if doc:
            doc_probe = _synth_path(doc) if "*" in doc else doc
            yield ("doc-sync: sensitive file + its doc MUST PASS",
                   lambda: bool(_fds.failures([probe, doc_probe], cfg)), False)
        if cfg.doc_sync_escape_globs:
            esc = _synth_path(cfg.doc_sync_escape_globs[0])
            yield ("doc-sync: escape glob (impact report) MUST PASS",
                   lambda: bool(_fds.failures([probe, esc], cfg)), False)
    else:
        yield ("doc-sync: (no [[doc_sync]] rules configured — skipped)", None, None)

    # --- vault fixtures (temp dir mirroring this repo's vocab)
    def vault_fixture(build):
        def run():
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                fcfg = Config(cfg.as_dict(), root)
                fcfg.knowledge_dir.mkdir(parents=True, exist_ok=True)
                fcfg.insights_dir.mkdir(parents=True, exist_ok=True)
                (fcfg.knowledge_dir / "index.md").write_text("# index\n", encoding="utf-8")
                build(fcfg)
                issues = (_vs.check_knowledge_index(fcfg)
                          + _vs.check_status_area(fcfg)
                          + _vs.check_provenance(fcfg))
                return any(level == "FAIL" for level, _ in issues)
        return run

    yield ("vault-sync: off-vocabulary status MUST FAIL",
           vault_fixture(lambda f: (f.insights_dir / "x.md").write_text(
               "---\ntype: insight\nstatus: not-a-real-status\n---\n", encoding="utf-8")), True)
    yield ("vault-sync: knowledge page missing from index MUST FAIL",
           vault_fixture(lambda f: ((f.knowledge_dir / "meta").mkdir(exist_ok=True),
                                    (f.knowledge_dir / "meta/ghost.md").write_text("# g\n", encoding="utf-8"))), True)
    yield ("vault-sync: broken source provenance MUST FAIL",
           vault_fixture(lambda f: ((f.knowledge_dir / "meta").mkdir(exist_ok=True),
                                    (f.knowledge_dir / "meta/p.md").write_text(
               "---\ntype: knowledge\nsources:\n  - raw/sources/ghost.md\n---\n", encoding="utf-8"))), True)

    def broken_link():
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.md").write_text("[x](missing.md)", encoding="utf-8")
            return bool(_dl.broken_doc_links(tmp))
    yield ("doc-links: broken relative link MUST FAIL", broken_link, True)


def main(argv=None):
    try:
        cfg = _config.load_config()
    except _config.ConfigError as e:
        print(f"canary: {e}")
        return 1

    failed = skipped = passed = 0
    for name, run, expect in _scenarios(cfg):
        if run is None:
            print(f"SKIP  {name}")
            skipped += 1
            continue
        got = run()
        if got == expect:
            print(f"OK    {name}")
            passed += 1
        else:
            print(f"FAIL  {name} (gate did not behave as expected)")
            failed += 1

    print(f"\ncanary: {passed} ok, {failed} broken gate(s), {skipped} skipped.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
