"""Create tournaments, add events, and choose formats.

Starting a tournament and managing the one you're on live on this one page —
a tournament isn't created until it has its first event, so the "first event"
fields are part of the same creation step rather than a separate page.

Entries and the draw for each event live on Players & entries → Event entries.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from tourney import i18n, models, rules
from tourney.constants import CATEGORY_ORDER, FORMAT_HELP, FORMAT_ORDER, SCORING_PRESETS
from tourney.i18n import tr
from views import ui


def _event_settings(key_prefix, available_categories):
    """Reactive (non-form) widgets for one event's category/format/scoring.

    These live outside any st.form on purpose: a form only reports its
    widgets' values on submit, so the format-specific settings below could
    never follow the format picker. Only the settings that belong to the
    chosen format are shown at all.
    """
    c1, c2 = st.columns(2)
    category = c1.selectbox(tr("Category"), available_categories, format_func=i18n.cat,
                            key=f"{key_prefix}_cat")
    fmt = c2.selectbox(tr("Format"), FORMAT_ORDER, format_func=i18n.fmt, key=f"{key_prefix}_fmt")
    st.caption(tr(FORMAT_HELP[fmt]))

    c3, c4 = st.columns(2)
    scoring = c3.selectbox(tr("Game scoring"), list(SCORING_PRESETS),
                           format_func=lambda k: i18n.preset_label(SCORING_PRESETS[k]),
                           key=f"{key_prefix}_scoring")
    best_of = c4.selectbox(tr("Match length"), [1, 3, 5], index=1,
                           format_func=lambda n: tr("Best of {n}", n=n), key=f"{key_prefix}_bo")
    system = st.radio(tr("Scoring system"), list(rules.SCORING_SYSTEMS), horizontal=True,
                      format_func=lambda k: tr(rules.SCORING_SYSTEMS[k]), key=f"{key_prefix}_sys",
                      help=tr("Side-out is the traditional USA Pickleball game: only the serving "
                              "side scores, two servers per side, 0-0-2 start. Rally scoring gives "
                              "a point on every rally."))

    # Only the chosen format's own settings — everything else keeps its default.
    swiss_rounds, pool_count, advance, gf_reset = 5, 2, 2, True
    if fmt == "swiss":
        st.markdown("**" + tr("Swiss settings") + "**")
        swiss_rounds = st.number_input(tr("Swiss rounds"), 1, 12, 5, key=f"{key_prefix}_sr",
                                       help=tr("How many rounds are paired before the event ends."))
    elif fmt == "pool_playoff":
        st.markdown("**" + tr("Pool play settings") + "**")
        c5, c6 = st.columns(2)
        pool_count = c5.number_input(tr("Pools"), 1, 12, 2, key=f"{key_prefix}_pc")
        advance = c6.number_input(tr("Advance per pool"), 1, 8, 2, key=f"{key_prefix}_adv",
                                  help=tr("How many entries from each pool reach the playoffs."))
    elif fmt == "double_elim":
        st.markdown("**" + tr("Double elimination settings") + "**")
        gf_reset = st.checkbox(
            tr("Allow a bracket reset"), value=True, key=f"{key_prefix}_gf",
            help=tr("If the losers-bracket survivor wins the grand final, both sides have one "
                    "loss, so a deciding match is created."))
    return {"category": category, "format": fmt, "scoring": scoring, "best_of": int(best_of),
            "scoring_system": system, "swiss_rounds": int(swiss_rounds),
            "pool_count": int(pool_count), "advance_per_pool": int(advance), "gf_reset": gf_reset}


def _create_event(tid, fields):
    models.create_event(
        tid, fields["category"], fields["format"], best_of=fields["best_of"],
        scoring=fields["scoring"], swiss_rounds=fields["swiss_rounds"],
        pool_count=fields["pool_count"], advance_per_pool=fields["advance_per_pool"],
        gf_reset=fields["gf_reset"], scoring_system=fields["scoring_system"],
        actor=ui.admin_name())


def _start_tournament():
    st.markdown("#### " + tr("Start a tournament"))
    st.caption(tr("A tournament needs at least one event before it exists — its first category "
                  "and format are set up right here, in the same step."))

    name = st.text_input(tr("Name"), placeholder="Saigon Open 2026", key="newt_name")
    c1, c2 = st.columns(2)
    venue = c1.text_input(tr("Venue"), placeholder="Thuan An Sports Centre", key="newt_venue")
    start = c2.date_input(tr("Start date"), value=date.today(), key="newt_start",
                          format="DD/MM/YYYY")
    end = c2.date_input(tr("End date"), value=date.today(), key="newt_end", format="DD/MM/YYYY")
    notes = st.text_area(tr("Notes"), placeholder=tr("Entry fee, court count, referee list…"),
                         height=80, key="newt_notes")

    st.markdown("##### " + tr("First event"))
    fields = _event_settings("newt_ev", CATEGORY_ORDER)

    if st.button(tr("Create tournament"), type="primary", key="newt_submit"):
        if not name.strip():
            st.error(tr("Give the tournament a name."))
            return
        tid = models.create_tournament(
            name, venue, str(start), str(end), notes, actor=ui.admin_name())
        try:
            _create_event(tid, fields)
        except models.RuleError as e:
            # Never leave an eventless tournament behind.
            models.delete_tournament(tid, actor=ui.admin_name())
            st.error(str(e))
            return
        st.session_state["tournament_id"] = tid
        st.success(tr("{name} created with its first event ({event}).",
                      name=name, event=i18n.cat(fields["category"])))
        st.rerun()


def _add_event(t):
    existing = {e["category"] for e in models.list_events(t["id"])}
    available = [c for c in CATEGORY_ORDER if c not in existing]
    if not available:
        st.caption(tr("All five categories are already in this tournament."))
        return
    st.markdown("#### " + tr("Add another event"))
    fields = _event_settings(f"addev_{t['id']}", available)
    if st.button(tr("Add event"), type="primary", key=f"addev_submit_{t['id']}"):
        try:
            _create_event(t["id"], fields)
            st.success(tr("{event} added.", event=i18n.cat(fields["category"])))
            st.rerun()
        except models.RuleError as e:
            st.error(str(e))


def _event_row(ev):
    entries = models.list_entries(ev["id"])
    matches = models.list_matches(ev["id"])
    header = tr("{event} · {format} — {e} entries, {m} matches · {status}",
                event=i18n.cat(ev["category"]), format=i18n.fmt(ev["format"]),
                e=len(entries), m=len(matches), status=i18n.status(ev["status"]))
    with st.expander(header, expanded=False):
        rule = models.scoring_rule(ev)
        st.caption(f"{i18n.preset_label(rule)} · {tr('best of {n}', n=ev['best_of'])} · "
                   f"{tr(rules.SCORING_SYSTEMS[models.scoring_system(ev)])}")

        if matches:
            played = sum(1 for m in matches if m["status"] in ("done", "bye"))
            st.progress(played / len(matches),
                        text=tr("{a} of {b} matches played", a=played, b=len(matches)))
        else:
            st.caption(tr("No draw yet."))

        st.info(tr("Add entries and set up, generate or clear the draw on the **Players & "
                   "entries** page → Event entries."))

        if st.button(tr("Delete this event"), key=f"del_{ev['id']}"):
            st.session_state[f"confirm_del_{ev['id']}"] = True
        if st.session_state.get(f"confirm_del_{ev['id']}"):
            st.warning(tr("Deletes the event, its entries and all its results."))
            if st.button(tr("Yes, delete"), key=f"del2_{ev['id']}", type="primary"):
                models.delete_event(ev["id"], actor=ui.admin_name())
                st.session_state.pop(f"confirm_del_{ev['id']}")
                st.rerun()


def render():
    ui.masthead(tr("Setup"), tr("Tournaments and events"))
    if not ui.require_admin(tr("create tournaments")):
        return

    tid = ui.current_tournament_id()
    t = models.get_tournament(tid) if tid else None

    with st.expander(tr("Start a new tournament"), expanded=t is None):
        _start_tournament()

    if not t:
        ui.empty_state(tr("Pick a tournament in the sidebar, or start one above."))
        return

    st.divider()
    st.markdown(f"### {t['name']}")
    st.caption(" · ".join(filter(None, [t["venue"], t["start_date"], i18n.status(t["status"])])))

    with st.expander(tr("Edit tournament details")):
        with st.form("edit_t"):
            name = st.text_input(tr("Name"), value=t["name"])
            venue = st.text_input(tr("Venue"), value=t["venue"] or "")
            statuses = ["setup", "running", "complete"]
            status = st.selectbox(tr("Status"), statuses, format_func=i18n.status,
                                  index=statuses.index(t["status"]))
            notes = st.text_area(tr("Notes"), value=t["notes"] or "", height=80)
            if st.form_submit_button(tr("Save changes")):
                from tourney import db
                db.update("tournaments", t["id"], {
                    "name": name, "venue": venue, "status": status, "notes": notes})
                st.success(tr("Saved."))
                st.rerun()

    st.divider()
    with st.expander(tr("Add another event")):
        _add_event(t)

    st.divider()
    st.markdown("#### " + tr("Events in this tournament"))
    events = models.list_events(t["id"])
    if not events:
        ui.empty_state(tr("No events yet — every tournament is created with one, so this should "
                          "not normally happen."))
    for ev in events:
        _event_row(ev)

    st.divider()
    with st.expander(tr("Danger zone")):
        st.caption(tr("Deleting a tournament removes its players, entries and every result."))
        confirm = st.text_input(tr("Type the tournament name to confirm"), key="del_t_name")
        if st.button(tr("Delete this tournament")):
            if confirm.strip() == t["name"]:
                models.delete_tournament(t["id"], actor=ui.admin_name())
                st.session_state.pop("tournament_id", None)
                st.success(tr("Deleted."))
                st.rerun()
            else:
                st.error(tr("The name does not match."))
