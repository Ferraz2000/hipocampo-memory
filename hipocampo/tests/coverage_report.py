#!/usr/bin/env python3
"""Zero-dependency line-coverage report for the ``hipocampo`` package.

Uses the standard-library :mod:`trace` module (no ``coverage`` install) so it
honors the kit's zero-dependency promise. Runs the full unittest suite under the
tracer, then prints per-module executed/executable line counts and a total.

Usage:
  python -m hipocampo.tests.coverage_report               # report only
  python -m hipocampo.tests.coverage_report --fail-under 80  # exit 1 if total < 80%

Caveats (so the number is read honestly):
- ``trace`` counts a line as covered only when it executes *during the traced
  run*. ``def``/``class`` statement lines run at import time (before tracing
  starts), so modules with many small methods/properties (e.g. ``config.py``)
  read lower than their real behavioral coverage. Treat the figure as a relative
  trend + a floor, not an absolute.
- ``[semantic]`` leaf functions only run when the optional extra is installed, so
  their lines read uncovered in the core (zero-dep) environment — expected.
"""

import argparse
import contextlib
import os
import sys
import trace
import unittest

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hipocampo/
_REPO_ROOT = os.path.dirname(_PKG_ROOT)


def _source_files():
    """Every ``hipocampo/**.py`` except the test suite and ``__init__`` shims."""
    for dirpath, _dirs, files in os.walk(_PKG_ROOT):
        if os.sep + "tests" in os.sep + os.path.relpath(dirpath, _REPO_ROOT):
            continue
        for fname in sorted(files):
            if fname.endswith(".py") and fname != "__init__.py":
                yield os.path.join(dirpath, fname)


def _run_suite_traced():
    tracer = trace.Trace(count=True, trace=False)
    suite = unittest.TestLoader().discover(_PKG_ROOT + "/tests")
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
    result_holder = {}

    def _go():
        # Modules under test print to stdout (validators, hooks); keep the report
        # clean by swallowing it during the run.
        with open(os.devnull, "w") as null, \
                contextlib.redirect_stdout(null), contextlib.redirect_stderr(null):
            result_holder["result"] = runner.run(suite)

    tracer.runfunc(_go)
    return tracer.results(), result_holder.get("result")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Stdlib line-coverage for hipocampo.")
    ap.add_argument("--fail-under", type=float, default=None,
                    help="exit 1 if total coverage is below this percentage")
    args = ap.parse_args(argv)

    results, test_result = _run_suite_traced()
    executed = {}
    for (fname, lineno), n in results.counts.items():
        if n:
            executed.setdefault(os.path.abspath(fname), set()).add(lineno)

    rows = []
    tot_exec = tot_total = 0
    for path in _source_files():
        executable = set(trace._find_executable_linenos(path))
        if not executable:
            continue
        hit = len(executed.get(path, set()) & executable)
        total = len(executable)
        tot_exec += hit
        tot_total += total
        rows.append((os.path.relpath(path, _REPO_ROOT), hit, total))

    rows.sort(key=lambda r: (r[1] / r[2], r[0]))
    width = max(len(r[0]) for r in rows)
    print(f"\n{'module':<{width}}  cover   lines")
    print("-" * (width + 16))
    for rel, hit, total in rows:
        print(f"{rel:<{width}}  {100*hit/total:5.1f}%  {hit:>4}/{total}")
    overall = 100 * tot_exec / tot_total if tot_total else 100.0
    print("-" * (width + 16))
    print(f"{'TOTAL':<{width}}  {overall:5.1f}%  {tot_exec:>4}/{tot_total}")

    if test_result is not None and not test_result.wasSuccessful():
        print("\nTESTS FAILED — coverage figures are unreliable.", file=sys.stderr)
        return 1
    if args.fail_under is not None and overall < args.fail_under:
        print(f"\nFAIL: total coverage {overall:.1f}% < required {args.fail_under:.1f}%",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
