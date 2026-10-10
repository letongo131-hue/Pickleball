"""Collects every string the app can pass to `tr()` — used by the
translation test (and handy for translators: `python -m tourney.i18n_catalog`
prints every string still missing a Vietnamese translation).

Two sources:
  * literals: every `tr("...")` call in the source, found by parsing it;
  * data: strings that reach `tr()` through a variable — theme names,
    scoring presets, format help, status words, draw methods, round names.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIRS = ("tourney", "views")
SOURCE_FILES = ("app.py",)


def _source_files():
    for d in SOURCE_DIRS:
        yield from sorted((ROOT / d).glob("*.py"))
    for f in SOURCE_FILES:
        yield ROOT / f


def literal_calls() -> tuple[set[str], list[str]]:
    """(strings, problems) — problems are tr() calls whose first argument is
    an f-string or other expression we can't check statically."""
    found: set[str] = set()
    problems: list[str] = []
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else None
            if name != "tr" or not node.args:
                continue
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                found.add(arg.value)
            elif isinstance(arg, ast.IfExp) and all(
                    isinstance(x, ast.Constant) and isinstance(x.value, str) for x in (arg.body, arg.orelse)):
                found.update((arg.body.value, arg.orelse.value))
            elif isinstance(arg, ast.JoinedStr):
                problems.append(f"{path.name}:{node.lineno} tr() given an f-string")
    return found, problems


def data_strings() -> set[str]:
    from . import i18n, rules
    from .constants import FORMAT_HELP, SCORING_PRESETS
    out: set[str] = set()
    out.update(rules.SCORING_SYSTEMS.values())
    out.update(p["label"] for p in SCORING_PRESETS.values())
    out.update(FORMAT_HELP.values())
    out.update(i18n._STATUS_EN.values())
    out.update(i18n._SIMPLE_ROUNDS)
    try:
        from views import brackets, ui
        out.update(brackets.METHOD_LABELS.values())
        out.update(t["label"] for t in ui.THEMES.values())
    except Exception:          # views need Streamlit; the engine-only catalogue still works
        pass
    return out


def all_strings() -> set[str]:
    lit, _problems = literal_calls()
    return lit | data_strings()


def missing_vi() -> list[str]:
    from .vi import VI
    return sorted(s for s in all_strings() if s not in VI)


if __name__ == "__main__":
    lit, problems = literal_calls()
    for p in problems:
        print("PROBLEM:", p)
    miss = missing_vi()
    print(f"{len(all_strings())} strings, {len(miss)} missing Vietnamese")
    for s in miss:
        print(repr(s))
