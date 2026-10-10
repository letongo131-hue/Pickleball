"""Bridge so `pytest` (and VSCode's Testing panel) can run the test scripts.

The test files are plain scripts — each one seeds its own database at import
time and calls sys.exit() at the end — so pytest must not import them
directly (pytest.ini restricts collection to this file). Instead each script
runs as its own subprocess here, exactly like `python run_tests.py` does,
and its output is shown when it fails.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
ENGINE_TESTS = ["test_engine", "test_schedule", "test_new_features", "test_rules"]
UI_TESTS = ["test_app", "test_themes", "test_live_quick_draw", "test_drag_drop", "test_i18n",
            "test_custom_bracket"]
HAS_STREAMLIT = importlib.util.find_spec("streamlit") is not None


def _run(name: str):
    env = dict(os.environ, PICKLEBALL_LOCAL="1", PYTHONIOENCODING="utf-8")
    env.setdefault("PICKLEBALL_DEFAULT_LANG", "en")
    env.pop("DATABASE_URL", None)
    proc = subprocess.run([sys.executable, str(TESTS / f"{name}.py")], cwd=str(TESTS),
                          env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        pytest.fail(f"{name} failed:\n{proc.stdout}\n{proc.stderr}", pytrace=False)


@pytest.mark.parametrize("name", ENGINE_TESTS)
def test_engine_suite(name):
    _run(name)


@pytest.mark.skipif(not HAS_STREAMLIT, reason="Streamlit not installed")
@pytest.mark.parametrize("name", UI_TESTS)
def test_ui_suite(name):
    _run(name)
