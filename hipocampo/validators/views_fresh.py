#!/usr/bin/env python3
"""Materialized-views freshness gate (opt-in).

The ``_generated/`` mirrors must match what the note frontmatter + dataview
blocks would produce right now — otherwise agents read a stale read-model.
Add ``"views_fresh"`` to ``validators`` in ``brain.config.toml`` to enforce;
regenerate with ``python -m hipocampo.views``.
"""

import sys

from .. import config as _config
from .. import views as _views


def main(argv=None):
    try:
        cfg = _config.load_config()
    except _config.ConfigError as e:
        print(f"views-fresh: {e}")
        return 1
    return _views.main(["--check"])


if __name__ == "__main__":
    sys.exit(main())
