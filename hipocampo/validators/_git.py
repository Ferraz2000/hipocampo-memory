"""Git diff helpers shared by the validators. Never raises — returns None on any
git failure so callers can skip gracefully (exit 0) rather than hard-fail.
"""

import os
import subprocess


def git(cfg, *args):
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(cfg.repo_root), capture_output=True, text=True
        )
    except FileNotFoundError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def _lines(raw):
    if raw is None:
        return None
    return [line.strip() for line in raw.splitlines() if line.strip()]


def staged_files(cfg):
    """Files staged for commit (HEAD vs index), or None if git is unavailable."""
    return _lines(git(cfg, "diff", "--cached", "--name-only"))


def changed_files(cfg, diff_range):
    return _lines(git(cfg, "diff", "--name-only", diff_range))


def resolve_range(cfg, override=None):
    """Resolve the branch diff range, in order: override -> CI env -> base branch.

    Returns ``(diff_range, source_label)`` or ``(None, None)`` when no base ref
    is available.
    """
    if override:
        return f"{override}...HEAD", f"--base {override}"

    base = os.environ.get("GITHUB_BASE_REF")
    if base:
        git(cfg, "fetch", "--no-tags", "--depth=50", "origin", base)
        return f"origin/{base}...HEAD", f"GITHUB_BASE_REF={base}"

    before = os.environ.get("GITHUB_EVENT_BEFORE")
    if before and set(before) != {"0"}:
        return f"{before}..HEAD", "GITHUB_EVENT_BEFORE"

    seen = set()
    for cand in (f"origin/{cfg.base_branch}", "origin/main", "origin/master", "origin/develop"):
        if cand in seen:
            continue
        seen.add(cand)
        if git(cfg, "rev-parse", "--verify", "--quiet", cand):
            return f"{cand}...HEAD", f"fallback {cand}"
    return None, None
