"""Install per-agent hipocampo assets into a consumer repo.

The Python core is agent-agnostic. This module keeps the thin Codex/Gemini
filesystem conventions testable instead of leaving them only in skill prose.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


AGENT_SKILL_DIRS = {
    "codex": Path(".agents") / "skills",
    "gemini": Path(".gemini") / "skills",
}


def scaffold_agent_assets(root: Path, kit_root: Path, agent: str) -> list[Path]:
    """Copy skills and hook/router wiring for ``agent`` into ``root``.

    Returns the paths created or updated. Existing Gemini settings are merged so
    unrelated keys and non-hipocampo hooks survive.
    """

    agent = agent.lower()
    if agent not in AGENT_SKILL_DIRS:
        raise ValueError(f"unknown agent: {agent}")

    root = Path(root)
    kit_root = Path(kit_root)
    touched: list[Path] = []

    skills_src = kit_root / "plugin" / "skills"
    skills_dst = root / AGENT_SKILL_DIRS[agent]
    shutil.copytree(skills_src, skills_dst, dirs_exist_ok=True)
    touched.append(skills_dst)

    if agent == "codex":
        hook_src = kit_root / "templates" / "hooks" / "codex" / "hooks.json"
        hook_dst = root / ".codex" / "hooks.json"
        hook_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(hook_src, hook_dst)
        touched.append(hook_dst)
        return touched

    settings_src = kit_root / "templates" / "hooks" / "gemini" / "settings.hooks.json"
    settings_dst = root / ".gemini" / "settings.json"
    settings_dst.parent.mkdir(parents=True, exist_ok=True)
    settings = _read_json_object(settings_dst)
    fragment = json.loads(settings_src.read_text(encoding="utf-8"))

    hooks = settings.setdefault("hooks", {})
    for event, entries in fragment["hooks"].items():
        hooks[event] = entries

    context = settings.setdefault("context", {})
    context["fileName"] = _with_router_files(context.get("fileName"))

    settings_dst.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    touched.append(settings_dst)
    return touched


def _read_json_object(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _with_router_files(value) -> list[str]:
    if isinstance(value, str):
        files = [value]
    elif isinstance(value, list):
        files = [str(item) for item in value]
    else:
        files = []
    for name in ("AGENTS.md", "GEMINI.md"):
        if name not in files:
            files.append(name)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m hipocampo.agents",
        description="Install Codex/Gemini skills and hook wiring into a repo.",
    )
    parser.add_argument("agents", nargs="+", choices=sorted(AGENT_SKILL_DIRS))
    parser.add_argument("--root", default=".", help="consumer repo root")
    parser.add_argument("--kit-root", default=".", help="hipocampo kit repo root")
    args = parser.parse_args(argv)

    for agent in args.agents:
        touched = scaffold_agent_assets(Path(args.root), Path(args.kit_root), agent)
        print(f"{agent}: " + ", ".join(str(p) for p in touched))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through tests/helpers.
    raise SystemExit(main())
