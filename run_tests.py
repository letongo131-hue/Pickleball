"""Run the whole test suite locally — Windows, macOS or Linux.

    python run_tests.py              # everything
    python run_tests.py --engine     # engine only: fast, no Streamlit needed
    python run_tests.py schedule     # just the tests whose name contains "schedule"
    python run_tests.py -v           # also print each test's own output when it passes

Every test runs in its own Python process against its own throwaway SQLite
file in your temp folder. Nothing here can touch pickleball.db or a Postgres
database from your secrets — the tests force local SQLite.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS = ROOT / "tests"

# Pure-engine tests: no Streamlit import anywhere on their path.
ENGINE_TESTS = ["test_engine", "test_schedule", "test_new_features", "test_rules"]
# Drive the real pages through streamlit.testing.v1.AppTest (headless, no browser).
UI_TESTS = ["test_app", "test_themes", "test_live_quick_draw", "test_drag_drop", "test_i18n",
            "test_custom_bracket"]


def _has_streamlit() -> bool:
    return importlib.util.find_spec("streamlit") is not None


def run_one(name: str, verbose: bool) -> tuple[bool, float, str]:
    env = dict(os.environ)
    env["PICKLEBALL_LOCAL"] = "1"
    env.setdefault("PICKLEBALL_DEFAULT_LANG", "en")
    env.pop("DATABASE_URL", None)
    env["PYTHONIOENCODING"] = "utf-8"
    started = time.time()
    proc = subprocess.run(
        [sys.executable, str(TESTS / f"{name}.py")],
        cwd=str(TESTS), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    took = time.time() - started
    out = proc.stdout + (("\n" + proc.stderr) if proc.stderr.strip() else "")
    return proc.returncode == 0, took, out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("filter", nargs="?", help="only run tests whose name contains this")
    ap.add_argument("--engine", action="store_true", help="engine tests only (no Streamlit)")
    ap.add_argument("--ui", action="store_true", help="UI (AppTest) tests only")
    ap.add_argument("-v", "--verbose", action="store_true", help="show output of passing tests")
    args = ap.parse_args()

    names = ENGINE_TESTS if args.engine else UI_TESTS if args.ui else ENGINE_TESTS + UI_TESTS
    if args.filter:
        names = [n for n in names if args.filter in n]
    if not names:
        print("No tests match.")
        return 1

    skipped = []
    if not _has_streamlit():
        skipped = [n for n in names if n in UI_TESTS]
        names = [n for n in names if n not in UI_TESTS]
        if skipped:
            print("Streamlit isn't installed, so the UI tests are skipped. "
                  "Run `pip install -r requirements.txt` to include them.\n")

    results = []
    for name in names:
        print(f"• {name} ...", end=" ", flush=True)
        ok, took, out = run_one(name, args.verbose)
        print(f"{'PASS' if ok else 'FAIL'}  ({took:.1f}s)")
        if not ok or args.verbose:
            print("    " + out.strip().replace("\n", "\n    ") + "\n")
        results.append((name, ok))

    failed = [n for n, ok in results if not ok]
    print("\n" + "-" * 48)
    print(f"{len(results) - len(failed)} passed, {len(failed)} failed"
          + (f", {len(skipped)} skipped" if skipped else ""))
    for n in failed:
        print(f"  FAILED: {n}   (re-run alone: python tests/{n}.py)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
