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


class ConfigError(Exception):
    """Raised for an unreadable/invalid brain.config.toml (actionable message)."""

# Canonical defaults. Mirror brain.config.example.toml — keep the two in sync.
DEFAULTS = {
    "vault_root": "docs/brain",
    "language": "en",
    # Interview answers recorded by /brain-init (read by the generator skills).
    "project_mode": "existing",  # "existing" | "greenfield"
    "team": False,               # true → PR-workflow rules + protected-branch suggestion
    "base_branch": "main",
    "stale_days": 365,
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
    # Where persona/preference captures land. Claude Code auto-loads
    # .claude/rules/USER.md; other agents (Codex/Gemini) read it via a pointer in
    # AGENTS.md — set this to a router-referenced path there (e.g. "<vault>/USER.md").
    "memory": {"persona_file": ".claude/rules/USER.md"},
    "inbox": {"decay_days": 30, "sweep_type": "capture-sweep"},
    "search": {
        "dirs": ["knowledge", "insights", "specs", "raw/sources"],
        # Terminal/dead-history statuses hidden from default search (--all shows them).
        "hidden_statuses": ["closed", "implemented", "rejected", "superseded", "deferred"],
    },
    "capture_triggers": [
        "decided", "decision is", "from now on", "always", "rule of thumb",
        "lesson learned", "trade-off", "anti-pattern", "canonical",
    ],
    # Phrases that count as a capture trigger only in AGENT messages (pattern
    # declarations), kept separate to cut noise from the agent's own narration.
    "capture_agent_triggers": ["anti-pattern", "canonical", "consolidated pattern"],
    # Hosts treated as internal — URLs containing these are NOT swept as sources.
    "capture_internal_hosts": ["localhost", "127.0.0.1"],
    "required_docs": [],
    "validators": ["doc_links", "feature_doc_sync", "vault_sync"],
    # How hard each gate point pushes back. Per point: "block" (fail the op),
    # "warn" (surface findings, never block), or "off" (skip). Defaults preserve
    # the historical blocking behavior; brain-scripts-init can relax local gates
    # (e.g. warn) while keeping CI strict. The git hooks/CI call `hipocampo.gate`,
    # which reads these — validators themselves always report truthfully.
    "enforcement": {"pre_commit": "block", "pre_push": "block", "ci": "block"},
    # router_lint is opt-in (not in the default validators): add "router_lint" to
    # validators to enforce a lean AGENTS.md. Lean routers measurably help agents.
    "router": {"file": "AGENTS.md", "max_lines": 120},
    # Directories doc_links never descends into (build/vendor output). ".git",
    # "__pycache__", and the cache dir are always excluded on top of these.
    # Materialized views: vault-relative dir whose notes feed dataview queries.
    "views": {"notes_root": "insights", "id_label": "Note"},
    # catalog_sync (opt-in validator): skills bundles <-> catalog doc + curated
    # required instruction files (subtree AGENTS.md contract).
    "catalog": {"skills_dirs": [], "catalog_doc": "", "required_files": [],
                "required_files_max_lines": 80},
    "doc_links_exclude_dirs": ["coverage", "node_modules", "bin", "obj", ".venv",
                                "dist", "build", "target", "vendor"],
    # Phrases that mean "the user already triggered capture this session" — the
    # Stop-hook sweep skips when it sees one (agent-agnostic; tune per setup).
    "capture_verbs": ["/capture", "registra isso", "save to the brain"],
    # Phase 12 semi-automatic capture — where the session-end sweep lands:
    #   "inbox" — sweep into the vault inbox (legacy default; git-versioned).
    #   "draft" — stage candidates in the disposable .brain-cache/ for review via
    #             `/capture --review`; nothing enters the vault without approval.
    #   "off"   — no sweep at all.
    # `max_candidates` caps how many candidates a draft sweep stages (cuts noise).
    "capture": {"auto": {"mode": "inbox", "max_candidates": 7}},
    # Phase 11 [semantic] tier — opt-in local-embedding search. OFF by default; the
    # core stays pure BM25/FTS5 and zero-dependency. When `enabled` AND the extra
    # (`pip install` of model2vec + sqlite-vec) imports AND sqlite can load
    # extensions, `index.search` fuses a vector ranking into the existing RRF.
    # Any of those absent ⇒ silent fallback to BM25. `dim` must match the model.
    "semantic": {"enabled": False, "model": "minishlab/potion-base-8M", "dim": 256},
    "doc_sync": [],
    # A changed file matching any of these globs (e.g. a Doc Impact Report)
    # satisfies every doc_sync rule for that commit.
    "doc_sync_escape_globs": ["**/doc-impact-reports/**/*.md"],
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
    def project_mode(self) -> str:
        return self._d["project_mode"]

    @property
    def team(self) -> bool:
        return bool(self._d["team"])

    @property
    def base_branch(self) -> str:
        return self._d["base_branch"]

    @property
    def stale_days(self) -> int:
        return int(self._d["stale_days"])

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

    # -- memory -----------------------------------------------------------
    @property
    def persona_file(self) -> str:
        """Repo-relative path where persona/preference captures land."""
        return self._d["memory"]["persona_file"]

    # -- inbox ------------------------------------------------------------
    @property
    def inbox_decay_days(self) -> int:
        return int(self._d["inbox"]["decay_days"])

    @property
    def inbox_sweep_type(self) -> str:
        return self._d["inbox"]["sweep_type"]

    # -- search -----------------------------------------------------------
    @property
    def search_dirs(self) -> list:
        return list(self._d["search"]["dirs"])

    @property
    def search_hidden_statuses(self) -> frozenset:
        return frozenset(self._d["search"]["hidden_statuses"])

    @property
    def vault_rel(self) -> str:
        """vault_root as a posix path relative to the repo root (for index prefixes)."""
        return self.vault_root.relative_to(self.repo_root).as_posix()

    # -- workflow ---------------------------------------------------------
    @property
    def capture_triggers(self) -> list:
        return list(self._d["capture_triggers"])

    @property
    def capture_agent_triggers(self) -> list:
        return list(self._d["capture_agent_triggers"])

    @property
    def capture_internal_hosts(self) -> list:
        return list(self._d["capture_internal_hosts"])

    @property
    def capture_verbs(self) -> list:
        return list(self._d["capture_verbs"])

    @property
    def capture_auto_mode(self) -> str:
        """Where the session-end sweep lands: "inbox" | "draft" | "off"."""
        return self._d["capture"]["auto"]["mode"]

    @property
    def capture_auto_max(self) -> int:
        """Cap on candidates a draft sweep stages."""
        return int(self._d["capture"]["auto"]["max_candidates"])

    # -- semantic tier (opt-in) ------------------------------------------
    @property
    def semantic_enabled(self) -> bool:
        return bool(self._d["semantic"]["enabled"])

    @property
    def semantic_model(self) -> str:
        return self._d["semantic"]["model"]

    @property
    def semantic_dim(self) -> int:
        return int(self._d["semantic"]["dim"])

    @property
    def views_notes_root(self) -> str:
        return self._d["views"]["notes_root"]

    @property
    def views_id_label(self) -> str:
        return self._d["views"]["id_label"]

    @property
    def catalog_skills_dirs(self) -> list:
        return list(self._d["catalog"]["skills_dirs"])

    @property
    def catalog_doc(self) -> str:
        return self._d["catalog"]["catalog_doc"]

    @property
    def catalog_required_files(self) -> list:
        return list(self._d["catalog"]["required_files"])

    @property
    def catalog_required_files_max_lines(self) -> int:
        return int(self._d["catalog"]["required_files_max_lines"])

    @property
    def doc_links_exclude_dirs(self) -> frozenset:
        return frozenset(self._d["doc_links_exclude_dirs"])

    @property
    def validators(self) -> list:
        return list(self._d["validators"])

    @property
    def required_docs(self) -> list:
        return list(self._d["required_docs"])

    @property
    def doc_sync(self) -> list:
        return list(self._d["doc_sync"])

    # -- enforcement ------------------------------------------------------
    @property
    def enforcement(self) -> dict:
        return dict(self._d["enforcement"])

    def enforcement_mode(self, point: str) -> str:
        """Gate mode for a point ("pre_commit"/"pre_push"/"ci"); block if unset."""
        return self._d["enforcement"].get(point, "block")

    @property
    def doc_sync_escape_globs(self) -> list:
        return list(self._d["doc_sync_escape_globs"])

    @property
    def router_file(self) -> str:
        return self._d["router"]["file"]

    @property
    def router_max_lines(self) -> int:
        return int(self._d["router"]["max_lines"])

    def as_dict(self) -> dict:
        """The fully-merged config as a plain dict (defaults + file overrides)."""
        return dict(self._d)


def _require_str_list(value, where):
    """Guard a field that must be a list of strings. A bare string is a common
    TOML slip and would be iterated character-by-character downstream (silently
    wrong), so fail fast with an actionable message instead."""
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ConfigError(
            f'{where} must be a list of strings — use {where} = ["..."], '
            f'not {where} = "...".'
        )


def _validate(data):
    """Fail fast on structurally invalid config that would otherwise misbehave."""
    doc_sync = data.get("doc_sync", [])
    if not isinstance(doc_sync, list):
        raise ConfigError("doc_sync must be a list of [[doc_sync]] rule tables.")
    for i, rule in enumerate(doc_sync):
        if not isinstance(rule, dict):
            raise ConfigError(f"doc_sync rule #{i + 1} must be a table.")
        label = rule.get("name", f"#{i + 1}")
        if "paths" in rule:
            _require_str_list(rule["paths"], f'doc_sync["{label}"].paths')
        if "docs" in rule:
            _require_str_list(rule["docs"], f'doc_sync["{label}"].docs')
    _require_str_list(data.get("doc_sync_escape_globs", []), "doc_sync_escape_globs")

    enforcement = data.get("enforcement", {})
    if not isinstance(enforcement, dict):
        raise ConfigError("enforcement must be a table of point = mode entries.")
    for point, mode in enforcement.items():
        if mode not in ("block", "warn", "off"):
            raise ConfigError(
                f'enforcement.{point} must be "block", "warn", or "off" (got {mode!r}).')

    auto_mode = data.get("capture", {}).get("auto", {}).get("mode", "inbox")
    if auto_mode not in ("inbox", "draft", "off"):
        raise ConfigError(
            f'capture.auto.mode must be "inbox", "draft", or "off" (got {auto_mode!r}).')

    sem = data.get("semantic", {})
    if not isinstance(sem, dict):
        raise ConfigError("semantic must be a table.")
    if "enabled" in sem and not isinstance(sem["enabled"], bool):
        raise ConfigError(f'semantic.enabled must be true or false (got {sem["enabled"]!r}).')

    # Closed-vocabulary and path lists: a bare string here is a common TOML slip
    # that would be iterated character-by-character downstream (silently wrong).
    for key in ("areas", "statuses", "active_states", "inactive_statuses"):
        if key in data:
            _require_str_list(data[key], key)
    search = data.get("search", {})
    if isinstance(search, dict) and "dirs" in search:
        _require_str_list(search["dirs"], "search.dirs")
    language = data.get("language")
    if language is not None and not isinstance(language, str):
        raise ConfigError(f"language must be a string (got {language!r}).")
    project_mode = data.get("project_mode")
    if project_mode is not None and project_mode not in ("existing", "greenfield"):
        raise ConfigError(
            f'project_mode must be "existing" or "greenfield" (got {project_mode!r}).')
    if "team" in data and not isinstance(data["team"], bool):
        raise ConfigError(f"team must be true or false (got {data['team']!r}).")
    dirs = data.get("dirs", {})
    if not isinstance(dirs, dict):
        raise ConfigError("dirs must be a table of name = path entries.")
    for name, val in dirs.items():
        if not isinstance(val, str):
            raise ConfigError(f"dirs.{name} must be a string path (got {val!r}).")


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

    def _load_toml(path):
        try:
            with open(path, "rb") as fh:
                return tomllib.load(fh)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"Invalid TOML in {path}: {e}") from None

    data = DEFAULTS
    if config_path:
        data = deep_merge(data, _load_toml(config_path))
        local_path = config_path.parent / LOCAL_OVERRIDE_FILENAME
        if local_path.is_file():
            data = deep_merge(data, _load_toml(local_path))

    _validate(data)
    return Config(data, root, config_path)
