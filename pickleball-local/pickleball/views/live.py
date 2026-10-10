"""Live board — the screen you put on the wall at the venue.

Scores as they happen, who's next, and where everyone stands. Nothing else:
no activity feed, no ready-to-call counters, no completion bars — those live
on the pages admins actually run the event from.
"""

from __future__ import annotations

import streamlit as st

from tourney import i18n, models, standings
from tourney.constants import CATEGORIES, STATUS_BYE, STATUS_DONE, STATUS_LIVE, STATUS_PENDING
from tourney.i18n import tr
from views import ui


def _gather(tournament_id):
    events = models.list_events(tournament_id)
    ev_by_id = {e["id"]: e for e in events}
    emap = models.entries_map_for_tournament(tournament_id)
    games = models.games_for_tournament(tournament_id)
    live, upcoming, done = [], [], []
    for m in models.list_matches_for_tournament(tournament_id):
        if m["status"] == STATUS_LIVE:
            live.append(m)
        elif m["status"] == STATUS_PENDING and models.match_ready(m):
            upcoming.append(m)
        elif m["status"] in (STATUS_DONE, STATUS_BYE):
            done.append(m)
    done.sort(key=lambda m: (m["finished_at"] or "", m["id"]), reverse=True)
    upcoming.sort(key=lambda m: (m["event_id"], m["round_no"], m["match_no"]))
    live.sort(key=lambda m: (m["court"] or "zz", m["started_at"] or ""))
    return ev_by_id, emap, games, live, upcoming, done


@st.fragment(run_every="6s")
def _board(tournament_id):
    ev_by_id, emap, games, live, upcoming, done = _gather(tournament_id)

    on_court = i18n.t("live.on_court")
    st.markdown(f"### 🟢 {on_court} ({len(live)})" if live else f"### 🟢 {on_court}")
    if live:
        ui.render_live_grid(live, emap, games, ev_by_id)
    else:
        ui.empty_state(i18n.t("live.nothing_on_court"))

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"### {i18n.t('live.next_up')}")
        if upcoming:
            for m in upcoming[:8]:
                ui.render_upcoming(m, emap, ev_by_id.get(m["event_id"]))
            if len(upcoming) > 8:
                st.caption(f"+ {len(upcoming) - 8} {i18n.t('live.more_waiting')}")
        else:
            ui.empty_state(i18n.t("live.no_matches_ready"))
    with c2:
        st.markdown(f"### {i18n.t('live.just_finished')}")
        if done:
            for m in done[:8]:
                ui.render_result(m, emap, games.get(m["id"], []), ev_by_id.get(m["event_id"]))
        else:
            ui.empty_state(i18n.t("live.no_results"))


@st.fragment(run_every="25s")
def _rankings(tournament_id):
    st.markdown(f"### {i18n.t('live.rankings')}")
    events = models.list_events(tournament_id)
    if not events:
        ui.empty_state(i18n.t("live.no_events"))
        return
    tabs = st.tabs([i18n.category_label(e["category"], CATEGORIES[e["category"]]) for e in events])
    for tab, ev in zip(tabs, events):
        with tab:
            rows = standings.event_table(ev["id"])
            if not rows:
                ui.empty_state(i18n.t("live.no_entries"))
                continue
            done = ev["status"] == "complete"
            st.caption(i18n.t("live.final_standings") if done else i18n.t("live.standings_so_far"))
            st.dataframe(ui.standings_frame(rows[:8], swiss=ev["format"] == "swiss"),
                         hide_index=True, width="stretch")


def render():
    t = ui.need_tournament()
    if not t:
        return
    ui.masthead(t["venue"] or tr("Live board"), t["name"])

    if not models.list_events(t["id"]):
        ui.empty_state(i18n.t("live.no_events"))
        return

    _board(t["id"])
    st.divider()
    _rankings(t["id"])
