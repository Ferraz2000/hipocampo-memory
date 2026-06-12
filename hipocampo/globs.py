"""Path glob matching with ``**`` support — stdlib only.

``fnmatch`` treats ``*`` as crossing ``/``, which is wrong for path rules. This
implements the familiar gitignore-style semantics:

- ``**`` matches any number of path segments (including zero).
- ``**/`` matches zero or more leading segments.
- ``*`` matches within a single segment (never crosses ``/``).
- ``?`` matches a single non-``/`` character.

Used by the doc-sync validator to map changed files to rules.
"""

import re
from functools import lru_cache


@lru_cache(maxsize=512)
def glob_to_regex(glob: str) -> "re.Pattern":
    i, n = 0, len(glob)
    out = ["(?s:"]
    while i < n:
        if glob[i:i + 3] == "**/":
            out.append("(?:.*/)?")
            i += 3
        elif glob[i:i + 2] == "**":
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    out.append(r")\Z")
    return re.compile("".join(out))


def match(path: str, glob: str) -> bool:
    return glob_to_regex(glob).match(path) is not None


def match_any(path: str, globs) -> bool:
    return any(match(path, g) for g in globs)
