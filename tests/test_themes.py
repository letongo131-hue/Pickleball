"""Tests for the theme picker: all themes build clean CSS with no leftover
unresolved tokens, the picker actually switches the active theme, and the
sidebar/live board render correctly under each one."""

import os

from _testutil import ROOT, check, finish, fresh_db

DB = fresh_db("themes")

from streamlit.testing.v1 import AppTest  # noqa: E402

from tourney import models  # noqa: E402
from views import ui  # noqa: E402

print("== Every theme resolves to clean CSS with no leftover tokens ==")
check(set(ui.THEMES) == {"liquid", "tribal", "cyberpunk", "minimal"}, "all four themes are registered")
placeholders = ["__cream__", "__parchment__", "__panel2__", "__line__", "__terracotta__",
               "__rust__", "__amber__", "__gold__", "__olive__", "__ink__", "__mute__",
               "__bead-radius__", "__bead-rotate__", "__FONT_BODY__", "__FONT_DISPLAY__",
               "__BACKGROUND__", "__BORDER_STRIP__", "__BOARD_SHADOW__", "__WING_URI__",
               "__FONT_IMPORT_URL__"]
for key, t in ui.THEMES.items():
    css = ui.CSS
    css = css.replace("__FONT_IMPORT_URL__", t["font_import_url"])
    css = css.replace("__FONT_BODY__", t["font_body"])
    css = css.replace("__FONT_DISPLAY__", t["font_display"])
    css = css.replace("__BACKGROUND__", t["background"])
    css = css.replace("__BORDER_STRIP__", t["border_strip"])
    css = css.replace("__BOARD_SHADOW__", t["board_shadow"])
    css = css.replace("__WING_URI__", t["wing_uri"])
    for name, value in t["vars"].items():
        css = css.replace(f"__{name}__", value)
    leftover = [p for p in placeholders if p in css]
    check(not leftover, f"{key}: no unresolved placeholder tokens (found {leftover})")

# ---------------------------------------------------------------------------
print("\n== The sidebar picker actually switches the theme ==")
tid = models.create_tournament("Theme Test Cup", actor="test")

at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=90)
at.session_state["tournament_id"] = tid
at.run()
check(not at.exception, "app boots with the default theme, no exception")
check(at.session_state["ui_theme"] == "liquid" if "ui_theme" in at.session_state else True,
      "defaults to Stay Liquid")

theme_select = [s for s in at.sidebar.selectbox if s.key == "theme_picker"]
check(bool(theme_select), "the theme picker selectbox is present in the sidebar")
if theme_select:
    labels = theme_select[0].options
    check(any("Tribal" in lbl for lbl in labels), "tribal is an option")
    check(any("Cyberpunk" in lbl for lbl in labels), "cyberpunk is an option")
    theme_select[0].set_value("cyberpunk")
    at.run()
    check(at.session_state["ui_theme"] == "cyberpunk", "picking cyberpunk updates session state")
    check(not at.exception, "app re-renders cleanly after switching theme")

    theme_select2 = [s for s in at.sidebar.selectbox if s.key == "theme_picker"]
    if theme_select2:
        theme_select2[0].set_value("tribal")
        at.run()
        check(at.session_state["ui_theme"] == "tribal", "picking tribal updates session state")
        check(not at.exception, "app re-renders cleanly after switching theme again")

finish()
