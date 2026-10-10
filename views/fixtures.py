"""Fixture editing.

Every change here runs through the same guard: if the two entries you are about
to put on court already meet somewhere else in this event, the save is refused
and the app names the fixture where they meet. You can override it deliberately,
which is what you want for a Swiss round where no clean pairing exists.
"""

from __future__ import annotations

import streamlit as st

from tourney import i18n, models
from tourney.i18n import tr
from tourney.constants import CATEGORIES, STATUS_LIVE, STATUS_PENDING
from views import ui


def _editable(matches):
    return [m for m in matches if m["status"] in (STATUS_PENDING, STATUS_LIVE)]


def _label(m, emap):
    a = emap.get(m["entry_a_id"], {}).get("name", tr("TBD"))
    b = emap.get(m["entry_b_id"], {}).get("name", tr("TBD"))
    return f"{ui.match_title(m)} — {a} {tr('vs')} {b}"


def _reassign_tab(ev, emap, entries):
    matches = _editable(models.list_matches(ev["id"]))
    if not matches:
        ui.empty_state(tr("Nothing left to change — every match is finished."))
        return

    mid = st.selectbox(tr("Fixture"), [m["id"] for m in matches],
                       format_func=lambda i: _label(next(m for m in matches if m["id"] == i), emap),
                       key="reassign_match")
    m = models.get_match(mid)
    if m["status"] == STATUS_LIVE:
        st.warning(tr("This match is on court. Changing it now will confuse the referee."))

    opts = [0] + [e["id"] for e in entries]

    def fmt(i):
        return tr("— empty —") if i == 0 else emap.get(i, {}).get("name", "?")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**" + tr("Side A") + "**")
        a = st.selectbox(tr("Entry A"), opts, index=opts.index(m["entry_a_id"]) if m["entry_a_id"] in opts else 0,
                         format_func=fmt, key="slot_a", label_visibility="collapsed")
    with c2:
        st.markdown("**" + tr("Side B") + "**")
        b = st.selectbox(tr("Entry B"), opts, index=opts.index(m["entry_b_id"]) if m["entry_b_id"] in opts else 0,
                         format_func=fmt, key="slot_b", label_visibility="collapsed")

    # Live preview of the conflict before anything is saved.
    if a and b:
        prior = models.have_met(ev["id"], a, b, exclude_match=mid)
        if prior:
            where = ", ".join(i18n.round_label(p["round_label"]) or tr("Match {n}", n=p["match_no"])
                              for p in prior)
            st.error(tr("{a} and {b} already meet in: {where}", a=fmt(a), b=fmt(b), where=where))
        else:
            st.success(tr("{a} vs {b} is a first meeting.", a=fmt(a), b=fmt(b)))

    allow = st.checkbox(tr("Allow a rematch anyway"), key="allow_rm",
                        help=tr("Use this when a Swiss round genuinely has no rematch-free pairing."))
    if st.button(tr("Save this fixture"), type="primary"):
        try:
            models.set_match_entry(mid, "A", a or None, actor=ui.admin_name(), allow_rematch=allow)
            models.set_match_entry(mid, "B", b or None, actor=ui.admin_name(), allow_rematch=allow)
            st.success(tr("Fixture updated."))
            st.rerun()
        except models.RuleError as e:
            st.error(str(e))


def _swap_tab(ev, emap):
    matches = [m for m in models.list_matches(ev["id"]) if m["status"] == STATUS_PENDING]
    if len(matches) < 2:
        ui.empty_state(tr("You need at least two unplayed fixtures to swap between."))
        return
    st.caption(tr("Exchange one side between two fixtures. Both resulting pairings are checked "
                  "for repeats before anything is written."))

    c1, c2 = st.columns(2)
    with c1:
        m1 = st.selectbox(tr("First fixture"), [m["id"] for m in matches],
                          format_func=lambda i: _label(next(m for m in matches if m["id"] == i), emap),
                          key="swap_m1")
        s1 = st.radio(tr("Side"), ["A", "B"], horizontal=True, key="swap_s1")
    with c2:
        rest = [m for m in matches if m["id"] != m1]
        m2 = st.selectbox(tr("Second fixture"), [m["id"] for m in rest],
                          format_func=lambda i: _label(next(m for m in rest if m["id"] == i), emap),
                          key="swap_m2")
        s2 = st.radio(tr("Side"), ["A", "B"], horizontal=True, key="swap_s2")

    ma, mb = models.get_match(m1), models.get_match(m2)
    va = ma["entry_a_id"] if s1 == "A" else ma["entry_b_id"]
    vb = mb["entry_a_id"] if s2 == "A" else mb["entry_b_id"]
    st.info(tr("Swapping {a} ↔ {b}", a=emap.get(va, {}).get("name", tr("empty")),
               b=emap.get(vb, {}).get("name", tr("empty"))))

    allow = st.checkbox(tr("Allow a rematch anyway"), key="swap_allow")
    if st.button(tr("Swap them"), type="primary"):
        try:
            models.swap_entries(m1, s1, m2, s2, actor=ui.admin_name(), allow_rematch=allow)
            st.success(tr("Swapped."))
            st.rerun()
        except models.RuleError as e:
            st.error(str(e))


def _courts_tab(ev, emap):
    matches = _editable(models.list_matches(ev["id"]))
    if not matches:
        ui.empty_state(tr("No open fixtures."))
        return
    st.caption(tr("Assign courts ahead of time so the Live board can show where to go."))
    c_fix, c_court, c_status = tr("Fixture"), tr("Court"), tr("Status")
    rows = st.data_editor(
        [{"id": m["id"], c_fix: _label(m, emap), c_court: m["court"] or "",
          c_status: i18n.status(m["status"])} for m in matches],
        column_config={"id": None,
                       c_fix: st.column_config.TextColumn(disabled=True),
                       c_status: st.column_config.TextColumn(disabled=True)},
        hide_index=True, width="stretch", key="court_editor")
    if st.button(tr("Save court assignments")):
        by_id = {m["id"]: m for m in matches}
        n = 0
        for r in rows:
            want = (r[c_court] or "").strip() or None
            if by_id[r["id"]]["court"] != want:
                models.set_court(r["id"], want, actor=ui.admin_name())
                n += 1
        st.success(tr("{n} court(s) updated.", n=n))
        st.rerun()


def _audit_tab(ev, emap):
    dupes = models.rematch_audit(ev["id"])
    if not dupes:
        st.success(tr("No pair is scheduled to meet more than once in this event."))
    else:
        st.warning(tr("{n} pair(s) meet more than once. That is expected in a "
                      "double-elimination bracket, and worth a second look anywhere else.",
                      n=len(dupes)))
        for d in dupes:
            a, b = d["entries"]
            names = f"{emap.get(a, {}).get('name', '?')} {tr('vs')} {emap.get(b, {}).get('name', '?')}"
            where = ", ".join(i18n.round_label(m["round_label"]) or tr("M{n}", n=m["match_no"])
                              for m in d["matches"])
            st.markdown(f"- **{names}** — {where}")

    orphans = [m for m in models.list_matches(ev["id"])
               if m["status"] == STATUS_PENDING and not models.match_ready(m)
               and not m["a_void"] and not m["b_void"]]
    st.caption(tr("{n} fixture(s) still waiting on an earlier result.", n=len(orphans)))


def render():
    t = ui.need_tournament()
    if not t:
        return
    ui.masthead(tr("Fixtures"), t["name"])
    if not ui.require_admin(tr("change fixtures")):
        return

    events = models.list_events(t["id"])
    if not events:
        ui.empty_state(tr("No events yet."))
        return
    eid = ui.event_picker(t["id"], key="fix_event")
    ev = models.get_event(eid)
    if not models.list_matches(eid):
        ui.empty_state(tr("This event has no draw yet."))
        return

    emap = models.entries_map(eid)
    entries = models.list_entries(eid)

    t1, t2, t3, t4 = st.tabs([tr("Reassign a fixture"), tr("Swap two sides"), tr("Courts"), tr("Repeat check")])
    with t1:
        _reassign_tab(ev, emap, entries)
    with t2:
        _swap_tab(ev, emap)
    with t3:
        _courts_tab(ev, emap)
    with t4:
        _audit_tab(ev, emap)
