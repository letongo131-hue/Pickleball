"""Pickleball tournament desk.

Run locally:   streamlit run app.py
               (or `python run_local.py` for a throwaway demo database)
"""

from __future__ import annotations

import hmac
import sys

if __name__ == "__main__":
    # Started with plain `python app.py` (or VSCode's ▶ "Run Python File")?
    # Streamlit apps need `streamlit run`, otherwise there is no server and you
    # only get "missing ScriptRunContext" warnings. Relaunch properly instead.
    from streamlit import runtime as _st_runtime

    if not _st_runtime.exists():
        import subprocess

        import os

        print("Starting via `streamlit run app.py` …  (Ctrl+C to stop)")
        here = os.path.dirname(os.path.abspath(__file__))
        # Run from the project folder so .streamlit/config.toml (light theme,
        # minimal toolbar) is always found, whatever folder you started in.
        env = dict(os.environ, STREAMLIT_THEME_BASE="light",
                   STREAMLIT_CLIENT_TOOLBAR_MODE="minimal")
        try:
            sys.exit(subprocess.call(
                [sys.executable, "-m", "streamlit", "run", os.path.join(here, "app.py"),
                 *sys.argv[1:]], cwd=here, env=env))
        except KeyboardInterrupt:
            sys.exit(0)

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Pickleball Tournament Desk", page_icon="🥒",
                   layout="wide", initial_sidebar_state="auto")

from tourney import db, i18n, models    # noqa: E402
from tourney.i18n import tr  # noqa: E402
from tourney.constants import ROLE_ADMIN, ROLE_REFEREE  # noqa: E402
from views import (brackets, courts, display, fixtures, live, players,  # noqa: E402
                   quick_match, scoring, setup, ui)

DEFAULT_PASSCODES = {ROLE_ADMIN: "pickle", ROLE_REFEREE: "referee"}
ROLE_SECRETS_SECTION = {ROLE_ADMIN: "admin", ROLE_REFEREE: "referee"}


# On hosts without a secrets.toml (Render, Railway, Fly.io…) set these instead.
ROLE_ENV = {ROLE_ADMIN: "PICKLEBALL_ADMIN_PASSCODE", ROLE_REFEREE: "PICKLEBALL_REFEREE_PASSCODE"}


def _passcodes(role: str) -> list[str]:
    import os

    raw = os.environ.get(ROLE_ENV[role], "").strip()
    if not raw:
        try:
            raw = st.secrets[ROLE_SECRETS_SECTION[role]]["passcode"]
        except Exception:
            return [DEFAULT_PASSCODES[role]]
    return [p.strip() for p in str(raw).split(",") if p.strip()]


def _check(role: str, code: str) -> bool:
    return any(hmac.compare_digest(code, p) for p in _passcodes(role))


def _using_default_passcodes() -> bool:
    return (_passcodes(ROLE_ADMIN) == [DEFAULT_PASSCODES[ROLE_ADMIN]]
            and _passcodes(ROLE_REFEREE) == [DEFAULT_PASSCODES[ROLE_REFEREE]])


def sidebar():
    st.sidebar.markdown(
        f"<div class='pk-brand'>Court<span class='accent'> &amp; </span>Council</div>"
        f"<div class='pk-brand-sub'>{i18n.t('brand.sub')}</div>",
        unsafe_allow_html=True)

    c1, c2 = st.sidebar.columns(2)
    theme_opts = ui.theme_options()
    theme_keys = list(theme_opts)
    current_theme = ui.current_theme_key()
    picked_theme = c1.selectbox(
        i18n.t("theme.label"), theme_keys,
        index=theme_keys.index(current_theme) if current_theme in theme_keys else 0,
        format_func=lambda k: theme_opts[k], key="theme_picker")
    if picked_theme != current_theme:
        ui.set_theme(picked_theme)
        st.rerun()

    lang_opts = i18n.lang_options()
    lang_keys = list(lang_opts)
    current_lang = i18n.current_lang()
    picked_lang = c2.selectbox(
        i18n.t("lang.label"), lang_keys,
        index=lang_keys.index(current_lang) if current_lang in lang_keys else 0,
        format_func=lambda k: lang_opts[k], key="lang_picker")
    if picked_lang != current_lang:
        i18n.set_lang(picked_lang)
        st.rerun()

    st.sidebar.divider()

    # --- tournament picker ------------------------------------------------
    tournaments = models.list_tournaments()
    if tournaments:
        ids = [t["id"] for t in tournaments]
        labels = {t["id"]: f"{t['name']}" + (f" · {t['start_date']}" if t["start_date"] else "")
                  for t in tournaments}
        current = st.session_state.get("tournament_id")
        idx = ids.index(current) if current in ids else 0
        picked = st.sidebar.selectbox(i18n.t("tournament.label"), ids, index=idx,
                                      format_func=lambda i: labels[i])
        st.session_state["tournament_id"] = picked
        t = models.get_tournament(picked)
        events = models.list_events(picked)
        st.sidebar.caption(tr("{e} event(s) · {p} players · {status}", e=len(events),
                              p=len(models.list_players(picked)), status=i18n.status(t["status"])))
    else:
        st.sidebar.info(tr("No tournaments yet. Sign in and create one on the Setup page."))

    st.sidebar.divider()

    # --- sign-in ------------------------------------------------------------
    # Three roles: Admin (setup, players, courts, fixtures — everything),
    # Referee (scoring desk only), Viewer (no sign-in, read-only).
    if ui.role() != "viewer":
        st.sidebar.success(f"{i18n.t('signin.signed_in_as')} **{ui.admin_name()}** · {ui.role_label()}")
        st.sidebar.caption(i18n.t("signin.several_people"))
        if st.sidebar.button(i18n.t("signin.signout"), width="stretch"):
            st.session_state["role"] = "viewer"
            st.session_state.pop("admin_name", None)
            st.rerun()
    else:
        with st.sidebar.form("signin"):
            st.markdown(f"**{i18n.t('signin.title')}**")
            name = st.text_input(i18n.t("signin.name"), placeholder="Anna")
            role_pick = st.selectbox(i18n.t("signin.role"), [ROLE_ADMIN, ROLE_REFEREE],
                                     format_func=lambda r: i18n.t(f"role.{r}"))
            code = st.text_input(i18n.t("signin.passcode"), type="password")
            if st.form_submit_button(i18n.t("signin.button"), width="stretch"):
                if not name.strip():
                    st.error(i18n.t("signin.name_required"))
                elif _check(role_pick, code):
                    st.session_state["role"] = role_pick
                    st.session_state["admin_name"] = name.strip()
                    st.rerun()
                else:
                    st.error(i18n.t("signin.wrong_passcode"))
        st.sidebar.caption(i18n.t("signin.viewer_note"))
        if _using_default_passcodes():
            st.sidebar.caption(tr(
                "Default passcodes: admin `{a}`, referee `{r}`. Set your own in "
                "`.streamlit/secrets.toml` before a real event.",
                a=DEFAULT_PASSCODES[ROLE_ADMIN], r=DEFAULT_PASSCODES[ROLE_REFEREE]))

    st.sidebar.divider()
    st.sidebar.caption(tr("Storage: {x}", x=db.describe()))


def main():
    ui.inject_css()
    sidebar()

    # Every view exposes a callable named `render`, so each page needs an
    # explicit url_path — Streamlit cannot infer unique routes otherwise.
    pages = [
        st.Page(live.render, title=i18n.t("nav.live"), icon="🟢", url_path="live", default=True),
        st.Page(brackets.render, title=i18n.t("nav.draws"), icon="🏆", url_path="draws"),
        st.Page(display.render, title=i18n.t("nav.venue"), icon="📺", url_path="display"),
        st.Page(scoring.render, title=i18n.t("nav.scoring"), icon="🎾", url_path="scoring"),
        st.Page(quick_match.render, title=i18n.t("nav.quick"), icon="⚡", url_path="quick"),
        st.Page(courts.render, title=i18n.t("nav.courts"), icon="📍", url_path="courts"),
        st.Page(fixtures.render, title=i18n.t("nav.fixtures"), icon="🔀", url_path="fixtures"),
        st.Page(players.render, title=i18n.t("nav.players"), icon="👥", url_path="players"),
        st.Page(setup.render, title=i18n.t("nav.setup"), icon="⚙️", url_path="setup"),
    ]
    # Viewers are read-only and never need the run-the-event pages, so that
    # whole nav section is hidden rather than just gated on each page —
    # nothing to see there means nothing to show there.
    nav = {i18n.t("nav.follow_along"): pages[:3]}
    if ui.role() != "viewer":
        nav[i18n.t("nav.run_event")] = pages[3:]
    st.navigation(nav).run()


if __name__ == "__main__":
    main()
