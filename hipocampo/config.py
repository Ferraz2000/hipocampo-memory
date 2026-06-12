"""Load and expose hipocampo's per-project configuration.

Everything project-specific (vault location, area/status vocabulary, doc-sync
rules, decay window, capture triggers, language) lives in ``brain.config.toml``
at the repo root. Scripts call :func:`load_config` and read from the returned
:class:`Config` instead of hardcoding constants.

Zero external dependencies: TOML is parsed with the standard-library
``tomllib`` (Python 3.11+). Any key omitted from the file falls back to
:data:`DEFAULTS`.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

CONFIG_FILENAME = "brain.config.toml"
LOCAL_OVERRIDE_FILENAME = "brain.config.local.toml"

# Canonical defaults. Mirror brain.config.example.toml — keep the two in sync.
DEFAULTS = {
    "vault_root": "docs/brain",
    "language": "en",
    "base_branch": "main",
    "dirs": {
        "knowledge": "knowledge",
        "inbox": "knowledge/_inbox",
        "insights": "insights",
        "raw_sources": "raw/sources",
        "generated": "_generated",
        "cache": ".brain-cache",
    },
    "areas": ["meta", "architecture", "product", "testing"],
    "statuses": [
        "triage", "active", "deferred",
        "implemented", "closed", "rejected", "superseded", "promoted",
    ],
    "active_states": ["ready", "in-progress"],
    "inactive_statuses": ["rejected", "closed", "discarded", "superseded", "implemented"],
    "area_aliases": {},
    "inbox": {"decay_days": 30, "sweep_type": "capture-sweep"},
    "capture_triggers": [
        "decided", "decision is", "from now on", "always", "rule of thumb",
        "lesson learned", "trade-off", "anti-pattern", "canonical",
    ],
    "validators": [],
    "doc_sync": [],
}


def deep_merge(base, override):
    """Recursively merge ``override`` onto a copy of ``base`` (dicts only)."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _find_up(start: Path, filename: str):
    """Nearest ``filename`` walking from ``start`` up to the filesystem root."""
    for parent in [start, *start.parents]:
        candidate = parent / filename
        if candidate.is_file():
            return candidate
    return None


def _find_repo_root(start: Path):
    """Nearest directory containing ``.git`` walking up; else ``start``."""
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return start


class Config:
    """Resolved configuration with path and vocabulary helpers.

    All ``*_dir`` properties return absolute :class:`pathlib.Path` objects.
    """

    def __init__(self, data: dict, repo_root: Path, config_path: Path | None = None):
        self._d = data
        self.repo_root = Path(repo_root)
        self.config_path = config_path

    # -- scalars ----------------------------------------------------------
    @property
    def language(self) -> str:
        return self._d["language"]

    @property
    def base_branch(self) -> str:
        return self._d["base_branch"]

    # -- paths ------------------------------------------------------------
    @property
    def vault_root(self) -> Path:
        return self.repo_root / self._d["vault_root"]

    def _vault_dir(self, key: str) -> Path:
        return self.vault_root / self._d["dirs"][key]

    @property
    def knowledge_dir(self) -> Path:
        return self._vault_dir("knowledge")

    @property
    def inbox_dir(self) -> Path:
        return self._vault_dir("inbox")

    @property
    def insights_dir(self) -> Path:
        return self._vault_dir("insights")

    @property
    def raw_sources_dir(self) -> Path:
        return self._vault_dir("raw_sources")

    @property
    def generated_dir(self) -> Path:
        return self._vault_dir("generated")

    @property
    def cache_dir(self) -> Path:
        # Cache is disposable and lives at the repo root, not inside the vault.
        return self.repo_root / self._d["dirs"]["cache"]

    # -- vocabulary -------------------------------------------------------
    @property
    def areas(self) -> list:
        return list(self._d["areas"])

    @property
    def statuses(self) -> frozenset:
        return frozenset(self._d["statuses"])

    @property
    def active_states(self) -> frozenset:
        return frozenset(self._d["active_states"])

    @property
    def inactive_statuses(self) -> frozenset:
        return frozenset(self._d["inactive_statuses"])

    @property
    def area_aliases(self) -> dict:
        return dict(self._d["area_aliases"])

    # -- inbox ------------------------------------------------------------
    @property
    def inbox_decay_days(self) -> int:
        return int(self._d["inbox"]["decay_days"])

    @property
    def inbox_sweep_type(self) -> str:
        return self._d["inbox"]["sweep_type"]

    # -- workflow ---------------------------------------------------------
    @property
    def capture_triggers(self) -> list:
        return list(self._d["capture_triggers"])

    @property
    def validators(self) -> list:
        return list(self._d["validators"])

    @property
    def doc_sync(self) -> list:
        return list(self._d["doc_sync"])

    def as_dict(self) -> dict:
        """The fully-merged config as a plain dict (defaults + file overrides)."""
        return dict(self._d)


def load_config(start=None) -> Config:
    """Find and load ``brain.config.toml``, merged over :data:`DEFAULTS`.

    Search starts at ``start`` (default: cwd) and walks up. A
    ``brain.config.local.toml`` next to it is merged last (machine-local,
    gitignored). When no config file is found, defaults are used and the repo
    root is the nearest ``.git`` ancestor (or the start directory).
    """
    start_path = Path(start or os.getcwd()).resolve()

    config_path = _find_up(start_path, CONFIG_FILENAME)
    root = config_path.parent if config_path else _find_repo_root(start_path)

    data = DEFAULTS
    if config_path:
        with open(config_path, "rb") as fh:
            data = deep_merge(data, tomllib.load(fh))
        local_path = config_path.parent / LOCAL_OVERRIDE_FILENAME
        if local_path.is_file():
            with open(local_path, "rb") as fh:
                data = deep_merge(data, tomllib.load(fh))

    return Config(data, root, config_path)
