"""Scoring desk — where admins and referees call matches on and score them.

Live matches use a point-by-point scoreboard: every +1/-1 tap writes to the
database immediately, so it's visible on the Live board (and to anyone else
looking at this same match) straight away, and every adjustment is logged —
not just the final score. A manual/typed entry is still available underneath
for corrections or recording a match that was played and scored elsewhere.
"""

from __future__ import annotations

import html

import streamlit as st

from tourney import db, formats, models, standings
from tourney.constants import (
    CATEGORIES, SCORING_PRESETS, STATUS_BYE, STATUS_DONE, STATUS_LIVE, STATUS_PENDING,
)
from tourney.i18n import tr
from views import referee, ui
from tourney import i18n


def _manual_score_form(m, ev, emap, key_prefix):
    """Bulk numeric entry — for retirements, corrections, or recording a
    match that was already played and scored somewhere else."""
    rule = models.scoring_rule(ev)
    best_of = m["best_of"]
    max_games = best_of
    existing = {g["game_no"]: g for g in models.get_games(m["id"])}
    a_name = emap.get(m["entry_a_id"], {}).get("name", "TBD")
    b_name = emap.get(m["entry_b_id"], {}).get("name", "TBD")

    st.caption(f"{i18n.preset_label(rule)} · {tr('best of {n}', n=best_of)}")
    n_games = st.number_input(tr("Games played"), min_value=1, max_value=max_games,
                              value=max(1, len(existing) or (best_of // 2 + 1)),
                              key=f"{key_prefix}_ng")
    retire = st.selectbox(tr("Retired?"), ["no", "A", "B"],
                          format_func=lambda r: {"no": tr("No"),
                                                 "A": tr("{name} retired", name=a_name),
                                                 "B": tr("{name} retired", name=b_name)}[r],
                          key=f"{key_prefix}_ret")

    games = []
    for i in range(1, int(n_games) + 1):
        g = existing.get(i)
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.markdown(f"<div style='padding-top:.55rem'>{tr('Game {n}', n=i)}</div>", unsafe_allow_html=True)
        a = c2.number_input(a_name, min_value=0, max_value=99,
                            value=int(g["score_a"]) if g else 0,
                            key=f"{key_prefix}_g{i}a", label_visibility="collapsed" if i > 1 else "visible")
        b = c3.number_input(b_name, min_value=0, max_value=99,
                            value=int(g["score_b"]) if g else 0,
                            key=f"{key_prefix}_g{i}b", label_visibility="collapsed" if i > 1 else "visible")
        games.append((int(a), int(b)))

    if st.button(tr("Save result"), key=f"{key_prefix}_save", type="primary"):
        retire_side = retire if retire in ("A", "B") else None
        try:
            models.submit_score(m["id"], games, actor=ui.admin_name(),
                                expected_version=m["version"], retire_side=retire_side)
            models.release_match(m["id"], ui.admin_name())
            st.success(tr("Result saved."))
            st.rerun()
        except models.ConflictError as e:
            st.error(str(e))
            if st.button(tr("Reload this match"), key=f"{key_prefix}_reload"):
                st.rerun()
        except models.RuleError as e:
            st.error(str(e))


def _score_form(m, ev, emap, key_prefix):
    """One expander per match: courts, scoring, save."""
    holder = models.claim_holder(m)
    if holder and holder != ui.admin_name():
        st.warning(tr("{who} is scoring this match right now. Check with them before you save.", who=holder))

    if m["status"] == STATUS_PENDING:
        referee.render_prematch(m, ev, emap, key_prefix)
        return

    if m["status"] == STATUS_LIVE:
        models.claim_match(m["id"], ui.admin_name())
        referee.render_live(m, ev, emap, key_prefix,
                            manual_form=lambda: _manual_score_form(m, ev, emap, key_prefix + "_manual"))
        return

    _manual_score_form(m, ev, emap, key_prefix)


def focused_match_list(matches, emap_fn, ev_fn, focus_key, key_ns, empty_msg=None):
    """Pick a match, then see only that one — the rest of the list stays out
    of the way until you back out. With several courts live at once, this is
    what keeps a referee's taps landing on the match they meant to score,
    and makes it obvious at a glance which one they're tracking.
    """
    empty_msg = empty_msg or tr("Every match here is finished.")
    live = [m for m in matches if m["status"] == STATUS_LIVE]
    ready = [m for m in matches if m["status"] == STATUS_PENDING and models.match_ready(m)]
    waiting = [m for m in matches if m["status"] == STATUS_PENDING and not models.match_ready(m)]

    focus_id = st.session_state.get(focus_key)
    if focus_id:
        m = models.get_match(focus_id)
        if m and m["status"] in (STATUS_LIVE, STATUS_PENDING):
            emap, ev = emap_fn(m), ev_fn(m)
            top1, top2 = st.columns([1, 2])
            if top1.button(tr("← All matches"), key=f"{key_ns}_back", width="stretch"):
                st.session_state.pop(focus_key, None)
                st.rerun()
            with top2:
                referee.fullscreen_toggle(key_ns)
            st.markdown(f'<p class="pk-ref-title">{html.escape(ui.match_title(m, ev))}</p>',
                        unsafe_allow_html=True)
            _score_form(m, ev, emap, f"{key_ns}_focus_{m['id']}")
            return
        st.session_state.pop(focus_key, None)   # finished, deleted, or stale — back to the list

    def _row(m):
        emap, ev = emap_fn(m), ev_fn(m)
        a = emap.get(m["entry_a_id"], {}).get("name", tr("TBD"))
        b = emap.get(m["entry_b_id"], {}).get("name", tr("TBD"))
        live_score = f"  ·  {m['cur_a']}–{m['cur_b']}" if m["status"] == STATUS_LIVE else ""
        holder = models.claim_holder(m)
        badge = tr(" — {who} scoring", who=holder) if holder else ""
        dot = "● " if m["status"] == STATUS_LIVE else ""
        with st.container(border=True):
            st.markdown(f"{dot}**{ui.match_title(m, ev)}**")
            st.caption(f"{a} {tr('vs')} {b}{live_score}{badge}")
            if st.button(tr("Score →"), key=f"{key_ns}_focusbtn_{m['id']}", width="stretch"):
                st.session_state[focus_key] = m["id"]
                st.rerun()

    if live:
        st.markdown("#### " + tr("On court ({n})", n=len(live)))
        for m in live:
            _row(m)
    if ready:
        st.markdown("#### " + tr("Ready to call ({n})", n=len(ready)))
        for m in ready:
            _row(m)
    if waiting:
        st.markdown("#### " + tr("Waiting on earlier results ({n})", n=len(waiting)))
        for m in waiting[:12]:
            emap, ev = emap_fn(m), ev_fn(m)
            a = emap.get(m["entry_a_id"], {}).get("name", tr("TBD"))
            b = emap.get(m["entry_b_id"], {}).get("name", tr("TBD"))
            st.caption(f"{ui.match_title(m, ev)} — {a} {tr('vs')} {b}")
    if not (live or ready or waiting):
        ui.empty_state(empty_msg)


@st.fragment(run_every="10s")
def _open_matches_tab(ev, emap):
    matches = models.list_matches(ev["id"])
    focused_match_list(matches, lambda m: emap, lambda m: ev,
                       focus_key=f"score_focus_{ev['id']}", key_ns=f"score_{ev['id']}")


def _finished_tab(ev, emap):
    matches = [m for m in models.list_matches(ev["id"])
               if m["status"] in (STATUS_DONE, STATUS_BYE)]
    if not matches:
        ui.empty_state(tr("No completed matches yet."))
        return
    games = models.games_for_event(ev["id"])
    matches.sort(key=lambda m: (m["finished_at"] or ""), reverse=True)
    st.caption(tr("{n} completed. Use 'Correct this result' if the desk typed it wrong.", n=len(matches)))
    for m in matches:
        ui.render_result(m, emap, games.get(m["id"], []), ev)
        with st.expander(tr("Correct this result")):
            if m["status"] == STATUS_BYE:
                st.caption(tr("Walkovers are corrected by editing the entry list."))
                continue
            c1, c2 = st.columns([1, 3])
            if c1.button(tr("Reopen"), key=f"reopen_{m['id']}"):
                try:
                    models.reopen_match(m["id"], actor=ui.admin_name())
                    st.success(tr("Reopened. It is back in Open matches — score it again there."))
                    st.rerun()
                except models.RuleError as e:
                    c2.error(str(e))
            c2.caption(tr("Reopening pulls the winner back out of the next round, so it only "
                          "works while that next match has not started."))


def _next_round_controls(ev):
    """Format-specific 'what happens next' actions."""
    if ev["format"] == "swiss":
        ready, why = formats.swiss_round_ready(ev["id"])
        played = formats.swiss_rounds_played(ev["id"])
        st.caption(tr("Round {a} of {b} scheduled.", a=played, b=ev["swiss_rounds"]))
        if ready:
            if st.button(tr("Pair round {n}", n=played + 1), type="primary", key=f"swiss_{ev['id']}"):
                try:
                    rnd, repeated = formats.build_swiss_round(ev["id"], actor=ui.admin_name())
                    if repeated:
                        st.warning(tr("Round {n} paired, but a rematch was unavoidable. "
                                      "Check the Fixtures page.", n=rnd))
                    else:
                        st.success(tr("Round {n} paired.", n=rnd))
                    st.rerun()
                except models.RuleError as e:
                    st.error(str(e))
        else:
            st.info(why)

    elif ev["format"] == "pool_playoff":
        has_playoff = any(m["stage"] == "playoff" for m in models.list_matches(ev["id"]))
        if has_playoff:
            st.caption(tr("Playoff bracket is live."))
        elif formats.pools_complete(ev["id"]):
            adv = st.number_input(tr("Advance per pool"), 1, 8, int(ev["advance_per_pool"] or 2),
                                  key=f"adv_{ev['id']}")
            if st.button(tr("Generate playoff bracket"), type="primary", key=f"po_{ev['id']}"):
                try:
                    formats.build_playoffs(ev["id"], advance_per_pool=int(adv),
                                           actor=ui.admin_name())
                    st.success(tr("Playoff bracket created."))
                    st.rerun()
                except models.RuleError as e:
                    st.error(str(e))
        else:
            st.info(tr("Finish every pool match, then the playoff bracket unlocks here."))
    else:
        st.caption(tr("This format schedules itself — results feed the next round automatically."))


def render():
    t = ui.need_tournament()
    if not t:
        return
    ui.masthead(tr("Scoring desk"), t["name"])
    if not ui.require_scorer(tr("enter scores")):
        return

    events = models.list_events(t["id"])
    if not events:
        ui.empty_state(tr("Add an event on the Setup page first."))
        return

    eid = ui.event_picker(t["id"], key="score_event")
    ev = models.get_event(eid)
    if not models.list_matches(eid):
        ui.empty_state(tr("This event has no draw yet. Generate it in Players & entries → Event entries."))
        return

    emap = models.entries_map(eid)
    tab_open, tab_done, tab_next = st.tabs([tr("Open matches"), tr("Finished"), tr("Next round")])
    with tab_open:
        _open_matches_tab(ev, emap)
    with tab_done:
        _finished_tab(ev, emap)
    with tab_next:
        _next_round_controls(ev)
