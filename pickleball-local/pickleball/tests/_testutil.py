"""Shared setup for every test script.

Each test gets its own throwaway SQLite file in the OS temp folder
(`%TEMP%\\pickleball-tests` on Windows, `/tmp/pickleball-tests` on Linux,
`$TMPDIR/pickleball-tests` on macOS) — never the real pickleball.db, and
never a Postgres URL from your secrets, even if you have one configured.

Import this *before* anything from `tourney` or `views`:

    from _testutil import ROOT, check, fresh_db, finish
    DB = fresh_db("engine")
"""

from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Windows consoles default to a legacy code page; the test output contains
# arrows and Vietnamese names, which would otherwise crash print().
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Streamlit's own AppTest constructor writes to session_state before any
# script is running, which logs a harmless "missing ScriptRunContext" warning
# on every page test. It's noise, not a problem — mute just that logger.
import logging  # noqa: E402

class _DropMissingCtx(logging.Filter):
    def filter(self, record):
        return "missing ScriptRunContext" not in record.getMessage()


# A filter rather than a log level: Streamlit resets its loggers' levels when
# it's imported, but leaves filters alone. Both logger names it uses:
for _name in ("streamlit.runtime.scriptrunner_utils.script_run_context", "streamlit"):
    logging.getLogger(_name).addFilter(_DropMissingCtx())

# The app defaults to Vietnamese; tests find widgets by their English labels.
# (tests/test_i18n.py switches to Vietnamese on purpose.)
os.environ.setdefault("PICKLEBALL_DEFAULT_LANG", "en")

# Never let a test fall through to a Postgres URL in secrets/env.
os.environ["PICKLEBALL_LOCAL"] = "1"
os.environ.pop("DATABASE_URL", None)

TEST_DIR = os.environ.get("PICKLEBALL_TEST_DIR") or os.path.join(
    tempfile.gettempdir(), "pickleball-tests")

FAILURES: list[str] = []


def fresh_db(name: str) -> str:
    """Point the engine at a brand-new empty SQLite file and return its path."""
    from tourney import db
    os.makedirs(TEST_DIR, exist_ok=True)
    return db.use_sqlite(os.path.join(TEST_DIR, f"{name}.db"), fresh=True)


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


def finish():
    print("\n" + ("ALL CHECKS PASSED" if not FAILURES else f"{len(FAILURES)} FAILURE(S)"))
    for f in FAILURES:
        print("  -", f)
    sys.exit(1 if FAILURES else 0)


def page_script(module: str, db_path: str, *, tournament_id=None, role=None,
                admin_name="Anna", lang=None) -> str:
    """A one-page Streamlit script that renders just `views.<module>` — what the
    UI tests feed to AppTest.from_string."""
    lines = [
        "import sys, os",
        f"sys.path.insert(0, {ROOT!r})",
        f"os.environ['PICKLEBALL_DB'] = {db_path!r}",
        "import streamlit as st",
        "st.set_page_config(layout='wide')",
        f"from views import ui, {module}",
    ]
    if tournament_id:
        lines.append(f"st.session_state['tournament_id'] = {tournament_id}")
    if role:
        lines.append(f"st.session_state['role'] = {role!r}")
        lines.append(f"st.session_state['admin_name'] = {admin_name!r}")
    if lang:
        lines.append(f"st.session_state['ui_lang'] = {lang!r}")
    lines += ["ui.inject_css()", f"{module}.render()"]
    return "\n".join(lines) + "\n"
