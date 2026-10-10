"""Quick match — start and score a one-off game that isn't part of any
tournament. Two names, a scoring format, and it's live; scoring reuses the
exact same point-by-point desk as a tournament match. Admins and referees
can both use this, same as the Scoring desk.
"""

from __future__ import annotations

import streamlit as st

from tourney import i18n, models, rules
from tourney.i18n import tr
from tourney.constants import SCORING_PRESETS
from views import scoring, ui


def _start_form():
    st.markdown("#### " + tr("Start a quick match"))
    st.caption(tr("Two names (four for doubles) and a scoring format — nothing else to set up. "
                  "This never touches any tournament's draws, entries, or standings."))
    with st.form("quick_start", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name_a = c1.text_input(tr("Side A"), placeholder="Lan")
        name_b = c2.text_input(tr("Side B"), placeholder="Minh")
        partner_a = c1.text_input(tr("Side A partner (doubles only)"), placeholder=tr("leave empty for singles"))
        partner_b = c2.text_input(tr("Side B partner (doubles only)"), placeholder=tr("leave empty for singles"))
        system = st.radio(tr("Scoring system"), list(rules.SCORING_SYSTEMS), horizontal=True,
                          format_func=lambda k: tr(rules.SCORING_SYSTEMS[k]))
        c3, c4 = st.columns(2)
        scoring_key = c3.selectbox(
            tr("Game scoring"), list(SCORING_PRESETS),
            format_func=lambda k: i18n.preset_label(SCORING_PRESETS[k]),
            index=list(SCORING_PRESETS).index("11_rally_2"))
        best_of = c4.selectbox(tr("Match length"), [1, 3, 5], index=1,
                               format_func=lambda n: tr("Best of {n}", n=n))
        if st.form_submit_button(tr("Start match"), type="primary"):
            if not name_a.strip() or not name_b.strip():
                st.error(tr("Both names are required."))
            else:
                try:
                    m = models.start_quick_match(name_a, name_b, scoring=scoring_key,
                                                 best_of=int(best_of), actor=ui.admin_name(),
                                                 scoring_system=system,
                                                 partner_a=partner_a, partner_b=partner_b)
                except models.RuleError as e:
                    st.error(str(e))
                else:
                    # Straight to the referee's pre-match screen: who serves,
                    # who starts on the right, a last check of the names.
                    st.session_state["quick_focus"] = m["id"]
                    st.rerun()


def _quick_list():
    matches = models.list_quick_matches()
    live_and_pending = [m for m in matches if m["status"] in ("live", "pending")]
    done = [m for m in matches if m["status"] == "done"][:10]

    empty_msg = (tr("Nothing in progress right now — see finished matches below.")
                 if done else tr("No quick matches yet — start one above."))
    scoring.focused_match_list(
        live_and_pending,
        emap_fn=lambda m: models.entries_map(m["event_id"]),
        ev_fn=lambda m: models.get_event(m["event_id"]),
        focus_key="quick_focus", key_ns="quick", empty_msg=empty_msg)

    if done:
        st.markdown("#### " + tr("Recently finished"))
        for m in done:
            ev = models.get_event(m["event_id"])
            emap = models.entries_map(m["event_id"])
            games = models.get_games(m["id"])
            ui.render_result(m, emap, games, ev)


def render():
    ui.masthead(tr("Quick match"), tr("Not part of any tournament"))
    if not ui.require_scorer(tr("start or score a quick match")):
        return
    if st.session_state.get("quick_focus"):
        _quick_list()          # refereeing one match: nothing else on screen
        return
    _start_form()
    st.divider()
    _quick_list()
