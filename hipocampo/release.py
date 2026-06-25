"""Release tooling — bump, changelog promotion, notes extraction, drift check.

Zero dependencies (stdlib only), same spirit as the rest of the kit. The version
is single-sourced in ``.claude-plugin/plugin.json``; this module keeps the
CHANGELOG and the README status lines in lockstep with it so a release is one
command instead of a hand-edited checklist (the manual process let
``README.pt-BR.md`` drift a whole minor version behind).

Subcommands::

    python -m hipocampo.release prepare X.Y.Z [--commit] [--tag] [--date D]
    python -m hipocampo.release prepare --minor            # bump from plugin.json
    python -m hipocampo.release notes  X.Y.Z               # print one section
    python -m hipocampo.release check                      # CI drift guard

``check`` fails (exit 1) on *version* drift across plugin.json / CHANGELOG /
READMEs — the release-critical invariant. A stale test-count in the status line
is only a warning (it legitimately changes on every test-adding PR; ``prepare``
regenerates it at release time).
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_PLUGIN = ".claude-plugin/plugin.json"
_CHANGELOG = "CHANGELOG.md"
_READMES = ("README.md", "README.pt-BR.md")
_TESTS_DIR = "hipocampo/tests"


# -- pure helpers (unit-tested) ------------------------------------------------

def parse_version(s: str):
    if not SEMVER.match(s.strip()):
        raise ValueError(f"not a X.Y.Z version: {s!r}")
    return tuple(int(p) for p in s.strip().split("."))


def bump(level: str, current: str) -> str:
    """Return the next version bumping ``current`` by ``level``."""
    major, minor, patch = parse_version(current)
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    if level == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown bump level: {level!r}")


def plugin_version(plugin_json_text: str):
    """The version string from plugin.json text (None if absent)."""
    m = re.search(r'"version"\s*:\s*"([^"]+)"', plugin_json_text)
    return m.group(1) if m else None


def set_plugin_version(plugin_json_text: str, ver: str) -> str:
    return re.sub(r'("version"\s*:\s*")[^"]+(")', rf"\g<1>{ver}\g<2>",
                  plugin_json_text, count=1)


def latest_changelog_version(changelog_text: str):
    """First released ``## [X.Y.Z]`` header (skips ``## [Unreleased]``)."""
    m = re.search(r"^## \[(\d+\.\d+\.\d+)\]", changelog_text, re.M)
    return m.group(1) if m else None


def promote_unreleased(changelog_text: str, ver: str, date: str) -> str:
    """Open a fresh ``[Unreleased]`` and stamp its current body as ``[ver] — date``."""
    marker = "## [Unreleased]"
    if marker + "\n" not in changelog_text:
        raise ValueError("CHANGELOG has no '## [Unreleased]' section to promote")
    return changelog_text.replace(
        marker + "\n", f"{marker}\n\n## [{ver}] — {date}\n", 1)


def extract_notes(changelog_text: str, ver: str) -> str:
    """The body of the ``## [ver]`` section (header excluded), trimmed."""
    out, capturing = [], False
    header = f"## [{ver}]"
    for line in changelog_text.splitlines():
        if line.startswith("## ["):
            if capturing:
                break
            capturing = line.startswith(header)
            continue
        if capturing:
            out.append(line)
    return "\n".join(out).strip()


def status_line_version(readme_text: str):
    m = re.search(r"\*\*Status:\s*v(\d+\.\d+\.\d+)", readme_text)
    return m.group(1) if m else None


def status_line_count(readme_text: str):
    m = re.search(r"\b(\d+)\s+(?:tests|testes)\b", readme_text)
    return int(m.group(1)) if m else None


def update_status_line(readme_text: str, ver: str, count: int) -> str:
    """Rewrite the version and the test count in the README status line."""
    text = re.sub(r"(\*\*Status:\s*v)\d+\.\d+\.\d+", rf"\g<1>{ver}",
                  readme_text, count=1)
    text = re.sub(r"\b\d+(\s+(?:tests|testes)\b)", rf"{count}\1", text, count=1)
    return text


# -- I/O wrappers --------------------------------------------------------------

def _repo() -> Path:
    """Nearest ancestor containing the plugin manifest (else cwd)."""
    here = Path.cwd().resolve()
    for parent in [here, *here.parents]:
        if (parent / _PLUGIN).is_file():
            return parent
    return here


def count_tests(repo: Path) -> int:
    import unittest
    return unittest.TestLoader().discover(str(repo / _TESTS_DIR)).countTestCases()


def _read(repo: Path, rel: str) -> str:
    return (repo / rel).read_text(encoding="utf-8")


def _write(repo: Path, rel: str, text: str) -> None:
    (repo / rel).write_text(text, encoding="utf-8")


# -- commands ------------------------------------------------------------------

def cmd_prepare(args) -> int:
    repo = _repo()
    current = plugin_version(_read(repo, _PLUGIN))
    if args.version:
        ver = args.version
        parse_version(ver)
    elif args.level:
        ver = bump(args.level, current)
    else:
        print("prepare: pass X.Y.Z or one of --major/--minor/--patch", file=sys.stderr)
        return 2
    date = args.date or datetime.date.today().isoformat()
    count = count_tests(repo)

    _write(repo, _PLUGIN, set_plugin_version(_read(repo, _PLUGIN), ver))
    _write(repo, _CHANGELOG, promote_unreleased(_read(repo, _CHANGELOG), ver, date))
    for rel in _READMES:
        _write(repo, rel, update_status_line(_read(repo, rel), ver, count))
    print(f"prepared v{ver} ({date}, {count} tests): plugin.json, CHANGELOG, READMEs")

    if args.commit or args.tag:
        subprocess.run(["git", "add", _PLUGIN, _CHANGELOG, *_READMES], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", f"chore(release): v{ver}"], cwd=repo, check=True)
        print(f"committed chore(release): v{ver}")
    if args.tag:
        # Annotated (-a), not lightweight: `git push --follow-tags` (the documented
        # flow) only pushes annotated tags, so a lightweight one would never ship.
        subprocess.run(["git", "tag", "-a", f"v{ver}", "-m", f"v{ver}"], cwd=repo, check=True)
        print(f"tagged v{ver} — push with: git push --follow-tags")
    return 0


def cmd_notes(args) -> int:
    repo = _repo()
    body = extract_notes(_read(repo, _CHANGELOG), args.version)
    if not body:
        print(f"notes: no CHANGELOG section for {args.version}", file=sys.stderr)
        return 1
    print(body)
    return 0


def check(repo: Path):
    """Return (errors, warnings). Errors are release-critical version drift."""
    errors, warnings = [], []
    pv = plugin_version(_read(repo, _PLUGIN))
    cv = latest_changelog_version(_read(repo, _CHANGELOG))
    if cv != pv:
        errors.append(f"CHANGELOG latest [{cv}] != plugin.json {pv}")
    for rel in _READMES:
        text = _read(repo, rel)
        rv = status_line_version(text)
        if rv != pv:
            errors.append(f"{rel} status line v{rv} != plugin.json {pv}")
    actual = count_tests(repo)
    for rel in _READMES:
        rc = status_line_count(_read(repo, rel))
        if rc != actual:
            warnings.append(f"{rel} status line {rc} tests != actual {actual} "
                            f"(refreshed at release by `prepare`)")
    return errors, warnings


def cmd_check(args) -> int:
    repo = _repo()
    errors, warnings = check(repo)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        print("release drift — run `python -m hipocampo.release prepare ...` or fix by hand.",
              file=sys.stderr)
        return 1
    print(f"release sync OK — version {plugin_version(_read(repo, _PLUGIN))}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hipocampo.release")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare", help="bump version + promote CHANGELOG + sync READMEs")
    p.add_argument("version", nargs="?", help="explicit X.Y.Z (else use a --level flag)")
    p.add_argument("--major", dest="level", action="store_const", const="major")
    p.add_argument("--minor", dest="level", action="store_const", const="minor")
    p.add_argument("--patch", dest="level", action="store_const", const="patch")
    p.add_argument("--date", help="release date (YYYY-MM-DD); default today")
    p.add_argument("--commit", action="store_true", help="also git commit the bump")
    p.add_argument("--tag", action="store_true", help="also git tag vX.Y.Z (implies --commit)")
    p.set_defaults(func=cmd_prepare)

    n = sub.add_parser("notes", help="print the CHANGELOG body for a version")
    n.add_argument("version")
    n.set_defaults(func=cmd_notes)

    c = sub.add_parser("check", help="fail on version drift (CI guard)")
    c.set_defaults(func=cmd_check)

    args = ap.parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
