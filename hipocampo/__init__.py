"""hipocampo — persistent, git-versioned, human-gated memory for coding agents.

Zero-dependency (standard library only). The package exposes a config loader and
a set of vault-maintenance tools that read everything project-specific from
``brain.config.toml`` instead of hardcoding it.
"""

from .config import Config, ConfigError, load_config

__all__ = ["Config", "ConfigError", "load_config"]
__version__ = "0.0.1"
