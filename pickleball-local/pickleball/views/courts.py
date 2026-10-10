"""Courts — deciding what goes on next, without double-booking anyone."""

from __future__ import annotations

import streamlit as st

from tourney import i18n, models, schedule
from tourney.i18n import tr
from tourney.constants import CATEGORIES, STATUS_LIVE
from views import ui


def _courts_setup(t):
    courts = models.list_courts(t["id"])
    c1, c2 = st.columns([2, 3])
    with c1:
        with st.form("add_court", clear_on_submit=True):
            name = st.text_input(tr("Court name"), placeholder=tr("Court 1"))
            if st.form_submit_button(tr("Add court"), type="primary"):
                try:
                    models.add_court(t["id"], name, actor=ui.admin_name())
                    st.rerun()
                except models.RuleError as e:
                    st.error(str(e))
    with c2:
        with st.form("bulk_courts", clear_on_submit=True):
            n = st.number_input(tr("Or add numbered courts"), 1, 24, 4)
            prefix = st.text_input(tr("Prefix"), value=tr("Court"))
            if st.form_submit_button(tr("Add them")):
                for i in range(1, int(n) + 1):
                    models.add_court(t["id"], f"{prefix} {i}", actor=ui.admin_name())
                st.rerun()

    if not courts:
        ui.empty_state(tr("No courts yet. Add them above so matches can be called on."))
        return

    st.markdown("**" + tr("Courts") + "**")
    for c in courts:
        col1, col2, col3 = st.columns([3, 2, 1])
        col1.markdown(f"**{c['name']}**")
        new_status = col2.selectbox(
            tr("Status"), ["open", "closed"], index=0 if c["status"] == "open" else 1,
            format_func=i18n.status, key=f"cs_{c['id']}", label_visibility="collapsed")
        if new_status != c["status"]:
            models.set_court_status(c["id"], new_status, actor=ui.admin_name())
            st.rerun()
        if col3.button(tr("Remove"), key=f"cd_{c['id']}"):
            try:
                models.delete_court(c["id"], actor=ui.admin_name())
                st.rerun()
            except models.RuleError as e:
                st.error(str(e))


def _call_next(t):
    ctx = schedule.tournament_context(t["id"])
    courts = models.list_courts(t["id"])
    if not courts:
        ui.empty_state(tr("Add courts on the Courts tab first."))
        return

    occupied = schedule.occupied_courts(ctx)
    free = schedule.free_courts(t["id"], ctx)

    st.markdown("#### " + tr("Courts right now"))
    cols = st.columns(min(4, len(courts)))
    for i, c in enumerate(courts):
        m = occupied.get(c["name"])
        with cols[i % len(cols)]:
            if c["status"] == "closed":
                st.markdown(f'<div class="pk-card"><div class="meta">{c["name"]}</div>'
                            f'<div class="row"><span class="side">{tr("Closed")}</span></div></div>',
                            unsafe_allow_html=True)
            elif m:
                ev = ctx["events"].get(m["event_id"], {})
                a = ctx["entries"].get(m["entry_a_id"], {}).get("name", tr("TBD"))
                b = ctx["entries"].get(m["entry_b_id"], {}).get("name", tr("TBD"))
                st.markdown(
                    f'<div class="pk-board"><div class="meta">'
                    f'<span class="pk-live-dot"></span><span>{c["name"]}</span>'
                    f'<span>{i18n.cat(ev["category"]) if ev.get("category") else ""}</span></div>'
                    f'<div class="row"><span class="side">{a}</span></div>'
                    f'<div class="row"><span class="side">{b}</span></div></div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="pk-card next"><div class="meta">{c["name"]}</div>'
                            f'<div class="row"><span class="side">{tr("Free")}</span></div></div>',
                            unsafe_allow_html=True)

    st.divider()
    plan = schedule.plan_next(t["id"], ctx)
    st.markdown("#### " + tr("Next to be called"))
    st.caption(tr("{n} court(s) free. Players already on court in another category "
                  "are skipped automatically.", n=len(free)))

    if plan["assignments"]:
        for a in plan["assignments"]:
            m, ev = a["match"], a["match"]["_event"]
            an = ctx["entries"].get(m["entry_a_id"], {}).get("name", tr("TBD"))
            bn = ctx["entries"].get(m["entry_b_id"], {}).get("name", tr("TBD"))
            st.markdown(
                f'<div class="pk-card next"><div class="meta">'
                f'{i18n.cat(ev["category"]) if ev.get("category") else ""} · {i18n.round_label(m["round_label"])} → '
                f'<strong>{a["court"]}</strong></div>'
                f'<div class="row"><span class="side">{an}</span></div>'
                f'<div class="row"><span class="side">{bn}</span></div></div>',
                unsafe_allow_html=True)
        if st.button(tr("Call these {n} match(es) on", n=len(plan["assignments"])),
                     type="primary", width="stretch"):
            n = schedule.call_matches(t["id"], plan["assignments"], actor=ui.admin_name())
            st.success(tr("{n} match(es) started.", n=n))
            st.rerun()
    else:
        ui.empty_state(tr("Nothing can be called right now."))

    if plan["blocked"]:
        with st.expander(tr("Held back ({n})", n=len(plan["blocked"]))):
            for b in plan["blocked"][:20]:
                m, ev = b["match"], b["match"]["_event"]
                an = ctx["entries"].get(m["entry_a_id"], {}).get("name", tr("TBD"))
                bn = ctx["entries"].get(m["entry_b_id"], {}).get("name", tr("TBD"))
                evn = i18n.cat(ev["category"]) if ev.get("category") else ""
                st.markdown(
                    f"- **{evn} · {i18n.round_label(m['round_label'])}** — "
                    f"{an} {tr('vs')} {bn}  \n  _{'; '.join(b['reasons'])}_")


def _manual(t):
    ctx = schedule.tournament_context(t["id"])
    queue = schedule.ready_queue(ctx)
    if not queue:
        ui.empty_state(tr("No matches are ready to call."))
        return
    courts = [c["name"] for c in models.list_courts(t["id"]) if c["status"] == "open"]
    if not courts:
        ui.empty_state(tr("Add courts on the Courts tab first."))
        return

    def label(mid):
        m = next(x for x in queue if x["id"] == mid)
        ev = m["_event"]
        an = ctx["entries"].get(m["entry_a_id"], {}).get("name", tr("TBD"))
        bn = ctx["entries"].get(m["entry_b_id"], {}).get("name", tr("TBD"))
        evn = i18n.cat(ev["category"]) if ev.get("category") else ""
        return f"{evn} · {i18n.round_label(m['round_label'])} — {an} {tr('vs')} {bn}"

    mid = st.selectbox(tr("Match"), [m["id"] for m in queue], format_func=label, key="man_match")
    m = next(x for x in queue if x["id"] == mid)
    occupied = schedule.occupied_courts(ctx)
    court = st.selectbox(tr("Court"), courts,
                         format_func=lambda c: c + (tr(" (in use)") if c in occupied else tr(" (free)")),
                         key="man_court")

    reasons = schedule.conflicts(m, ctx)
    if reasons:
        st.error(tr("Player clash: {x}", x="; ".join(reasons)))
    if court in occupied:
        st.warning(tr("{court} already has a live match on it.", court=court))
    if not reasons and court not in occupied:
        st.success(tr("No clash. Safe to call on."))

    override = st.checkbox(tr("Call it on anyway"), key="man_override",
                           help=tr("Use this when a player has agreed to play back to back, "
                                   "or you are moving a match mid-flight."))
    if st.button(tr("Call this match on"), type="primary"):
        if (reasons or court in occupied) and not override:
            st.error(tr("Tick 'Call it on anyway' to override the clash."))
        else:
            try:
                models.start_match(mid, actor=ui.admin_name(), court=court)
                st.success(tr("Called on."))
                st.rerun()
            except models.RuleError as e:
                st.error(str(e))


def _load(t):
    rows = schedule.player_schedule(t["id"])
    if not rows:
        ui.empty_state(tr("Nobody has matches outstanding."))
        return
    st.caption(tr("Players with matches still to play, busiest first. Use this to spot "
                  "someone who is about to be pulled three ways at once."))
    st.dataframe(
        [{tr("Player"): r["player"], tr("Club"): r["club"], tr("Entered in"): r["events"],
          tr("Matches left"): r["remaining"], tr("On court"): r["on_court"] or "—"} for r in rows],
        hide_index=True, width="stretch", height=460)


def render():
    t = ui.need_tournament()
    if not t:
        return
    ui.masthead(tr("Courts"), t["name"])
    if not ui.require_admin(tr("call matches on")):
        return

    t1, t2, t3, t4 = st.tabs([tr("Call next"), tr("Assign manually"), tr("Player load"), tr("Courts")])
    with t1:
        _call_next(t)
    with t2:
        _manual(t)
    with t3:
        _load(t)
    with t4:
        _courts_setup(t)
