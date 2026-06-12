"""Validators run by preflight (and individually by the git hooks / CI).

Each module exposes ``main(argv=None) -> int`` (0 = pass) so it works both as a
standalone CLI and when orchestrated by ``hipocampo.preflight``.
"""
