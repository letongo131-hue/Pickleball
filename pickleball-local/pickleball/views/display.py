"""Venue display — the screen you cast to a TV by the courts.

Read-only, no sidebar chrome competing for attention, oversized type meant to be
read from across a hall rather than at arm's length.
"""

from __future__ import annotations

import html

import streamlit as st

from tourney import i18n, models, schedule
from tourney.i18n import tr
from tourney.constants import CATEGORIES, STATUS_BYE, STATUS_DONE, STATUS_PENDING
from views import ui

DISPLAY_CSS = """
<style>
.pk-tv { font-family: var(--font-body); }
.pk-tv h2 {
  font-family: var(--font-body); font-weight: 700; font-size: .8rem; letter-spacing: .22em;
  text-transform: uppercase; color: var(--mute); margin: 1.1rem 0 .5rem;
  border-bottom: 1px solid var(--line); padding-bottom: .4rem;
}
.pk-court {
  background: var(--parchment); color: var(--ink); border-radius: 6px; padding: 1rem 1.15rem;
  margin-bottom: .7rem; position: relative;
  border-left: 3px solid var(--terracotta); box-shadow: 0 2px 8px color-mix(in srgb, var(--rust) 10%, transparent);
}
.pk-court .cname {
  font-family: var(--font-body); font-weight: 700; font-size: .78rem; letter-spacing: .2em;
  text-transform: uppercase; color: var(--terracotta); display: flex; align-items: center;
  gap: .6rem; margin-bottom: .6rem;
}
.pk-court .cat {
  font-family: var(--font-body); font-size: .72rem; letter-spacing: .1em;
  color: var(--mute); text-transform: uppercase;
}
.pk-court .srow {
  display: flex; justify-content: space-between; align-items: center; gap: .8rem; padding: .12rem 0;
}
.pk-court .who {
  font-family: var(--font-body); font-weight: 700; font-size: 1.3rem;
  line-height: 1.3; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.pk-court .who.leading { color: var(--rust); }
.pk-court .snum {
  font-family: var(--font-body); font-weight: 800; font-size: 2.1rem; line-height: 1;
  color: var(--terracotta); font-variant-numeric: tabular-nums; min-width: 1.2ch; text-align: right;
}
.pk-court .snum.leading { color: var(--rust); }
.pk-court .vs {
  font-family: var(--font-body); font-size: .68rem; color: var(--mute);
  letter-spacing: .2em; padding: .12rem 0; text-transform: uppercase;
}
.pk-court.idle { background: transparent; color: var(--mute); border: 1px dashed var(--line); border-left: 1px dashed var(--line); box-shadow: none; }
.pk-court.idle .cname { color: var(--mute); }
.pk-court.idle .who { font-size: 1.05rem; font-weight: 500; color: var(--mute); }

.pk-court-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px;
}

.pk-queue { background: var(--parchment); border: 1px solid var(--line); border-radius: 8px;
  padding: .6rem .8rem; margin-bottom: .4rem; display: flex; justify-content: space-between;
  align-items: baseline; gap: 1rem; }
.pk-queue .q-who { font-size: 1.02rem; font-weight: 600; color: var(--ink); }
.pk-queue .q-cat { font-family: var(--font-body); font-size: .64rem;
  letter-spacing: .13em; text-transform: uppercase; color: var(--mute); }
.pk-res { display: flex; justify-content: space-between; gap: 1rem; padding: .45rem .1rem;
  border-bottom: 1px solid var(--line); }
.pk-res .r-who { font-size: 1rem; color: var(--ink); }
.pk-res .r-who strong { font-weight: 700; color: var(--terracotta); }
.pk-res .r-pts { font-family: var(--font-body); font-variant-numeric: tabular-nums;
  font-size: .95rem; color: var(--mute); white-space: nowrap; font-weight: 600; }
</style>
"""


def _esc(s):
    return html.escape(str(s))


@st.fragment(run_every="6s")
def _board(tournament_id):
    ctx = schedule.tournament_context(tournament_id)
    courts = models.list_courts(tournament_id)
    occupied = schedule.occupied_courts(ctx)
    entries, events = ctx["entries"], ctx["events"]

    def nm(eid):
        return _esc(entries.get(eid, {}).get("name", tr("TBD")))

    def court_card_html(court_name, m):
        ev = events.get(m["event_id"], {})
        cur_a, cur_b = int(m.get("cur_a", 0) or 0), int(m.get("cur_b", 0) or 0)
        lead_a = " leading" if cur_a > cur_b else ""
        lead_b = " leading" if cur_b > cur_a else ""
        return (
            f'<div class="pk-court"><div class="cname">'
            f'<span class="pk-live-dot"></span>{_esc(court_name)}'
            f'<span class="cat">{_esc(i18n.cat(ev["category"]) if ev.get("category") else "")} · '
            f'{_esc(i18n.round_label(m.get("round_label")))}</span></div>'
            f'<div class="srow"><span class="who{lead_a}">{nm(m["entry_a_id"])}</span>'
            f'<span class="snum{lead_a}">{cur_a}</span></div>'
            f'<div class="vs">{tr("vs")}</div>'
            f'<div class="srow"><span class="who{lead_b}">{nm(m["entry_b_id"])}</span>'
            f'<span class="snum{lead_b}">{cur_b}</span></div></div>')

    st.markdown('<div class="pk-tv">', unsafe_allow_html=True)

    # --- courts: a responsive grid so 4 (or more) courts read clearly at once
    st.markdown(f"<h2>{tr('On court')}</h2>", unsafe_allow_html=True)
    cards = []
    if courts:
        for c in courts:
            m = occupied.get(c["name"])
            if m:
                cards.append(court_card_html(c["name"], m))
            else:
                label = tr("Closed") if c["status"] == "closed" else tr("Free")
                cards.append(f'<div class="pk-court idle"><div class="cname">{_esc(c["name"])}</div>'
                             f'<div class="who">{label}</div></div>')
    else:
        # Fall back to whatever is live even if courts were never registered.
        for m in ctx["matches"]:
            if m["status"] == "live":
                cards.append(court_card_html(m.get("court") or tr("Court TBD"), m))
    if cards:
        st.markdown(f'<div class="pk-court-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
    else:
        ui.empty_state(tr("No matches on court."))

    left, right = st.columns(2)

    # --- next up --------------------------------------------------------
    with left:
        st.markdown(f"<h2>{tr('Next up')}</h2>", unsafe_allow_html=True)
        queue = schedule.callable_queue(ctx)[:7]
        if queue:
            for m in queue:
                ev = m["_event"]
                st.markdown(
                    f'<div class="pk-queue"><span class="q-who">{nm(m["entry_a_id"])}'
                    f' <span class="q-cat">{tr("vs")}</span> {nm(m["entry_b_id"])}</span>'
                    f'<span class="q-cat">{_esc(i18n.cat(ev["category"]) if ev.get("category") else "")}</span>'
                    f'</div>', unsafe_allow_html=True)
        else:
            waiting = len(schedule.ready_queue(ctx))
            ui.empty_state(tr("{n} match(es) waiting on players who are still on court.", n=waiting)
                           if waiting else tr("Nothing waiting."))

    # --- results --------------------------------------------------------
    with right:
        st.markdown(f"<h2>{tr('Latest results')}</h2>", unsafe_allow_html=True)
        done = [m for m in ctx["matches"] if m["status"] in (STATUS_DONE, STATUS_BYE)]
        done.sort(key=lambda m: (m["finished_at"] or "", m["id"]), reverse=True)
        if done:
            games = models.games_for_tournament(tournament_id)
            for m in done[:8]:
                gs = games.get(m["id"], [])
                wa = m["winner_entry_id"] == m["entry_a_id"]
                a, b = nm(m["entry_a_id"]), nm(m["entry_b_id"])
                a = f"<strong>{a}</strong>" if wa else a
                b = f"<strong>{b}</strong>" if not wa else b
                pts = (" ".join(f"{g['score_a']}-{g['score_b']}" for g in gs)
                       if gs else tr("walkover"))
                st.markdown(
                    f'<div class="pk-res"><span class="r-who">{a} {tr("vs")} {b}</span>'
                    f'<span class="r-pts">{_esc(pts)}</span></div>', unsafe_allow_html=True)
        else:
            ui.empty_state(tr("No results yet."))

    st.markdown("</div>", unsafe_allow_html=True)


def render():
    t = ui.need_tournament()
    if not t:
        return
    st.markdown(DISPLAY_CSS, unsafe_allow_html=True)
    ui.masthead(t["venue"] or tr("Live"), t["name"])
    st.caption(tr("Refreshes on its own. Collapse the sidebar and press F11 to cast this "
                  "to a screen at the courts."))
    if not models.list_events(t["id"]):
        ui.empty_state(tr("No events yet."))
        return
    _board(t["id"])
