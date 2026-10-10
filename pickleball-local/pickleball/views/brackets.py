"""Brackets, pool tables and standings — the public-facing results view.

Setting a draw up (method, seed order, pools, the hand-built custom bracket)
happens in Players & entries → Event entries, in one place with the Generate
button. The building blocks live here and are called from there; this page
itself only shows results.
"""

from __future__ import annotations

import random

import streamlit as st
from streamlit_sortables import sort_items

from tourney import formats, i18n, models, standings
from tourney.constants import (
    POOL_NAMES, STAGE_GF, STAGE_LB, STAGE_PLAYOFF, STATUS_BYE, STATUS_DONE, STATUS_LIVE, STAGE_WB,
)
from tourney.i18n import tr
from views import ui

METHOD_LABELS = {
    "seed": "By seed",
    "random": "Randomize",
    "manual": "Manual (drawn outside the app)",
    "custom": "Custom (build the bracket by hand)",
}


def method_label(method: str) -> str:
    return tr(METHOD_LABELS.get(method, method))


def draw_method(event_id) -> str:
    """The method in use for this event. Once a draw exists this is read
    from the event itself (durable across reloads and different admins'
    sessions) — session state only holds the choice while it's still being
    made, before anything has been generated or built."""
    ev = models.get_event(event_id)
    if ev and ev.get("draw_method"):
        return ev["draw_method"]
    return st.session_state.get(f"draw_method_{event_id}", "seed")


def draw_setup(ev, entries) -> str:
    """Pre-draw, admin-only: choose how the draw is ordered, then put the
    confirmed entries in seed order or into pools by dragging them. Returns
    the chosen method."""
    method_key = f"draw_method_{ev['id']}"
    methods = list(METHOD_LABELS)
    method = st.radio(tr("Draw method"), methods,
                      index=methods.index(st.session_state.get(method_key, "seed")),
                      format_func=method_label, key=f"method_radio_{ev['id']}", horizontal=True)
    st.session_state[method_key] = method

    if method == "custom":
        custom_builder(ev, entries)
    elif ev["format"] == "pool_playoff" and method == "manual":
        _pool_setup(ev, entries)
    else:
        _seed_setup(ev, entries, method)
    return method


def custom_builder(ev, entries):
    """Build the bracket entirely by hand: pair entries into Round 1, then
    for every match pick exactly where its winner — and its loser too, if
    you want that side to keep playing — goes next round. Nothing here is
    computed automatically; every matchup and every advancement is a
    decision the admin makes explicitly."""
    matches = models.list_matches(ev["id"])
    st.caption(tr("Pair up entries into matches, then route each one's winner — and its loser, "
                  "if you want them to keep playing too — to an exact slot next round."))

    if not matches:
        _custom_round1(ev, entries)
        return

    conflicts = _routing_conflicts(matches)
    if conflicts:
        spots = ", ".join(tr("R{r} · slot {s}", r=models.get_match(tid)["round_no"], s=slot)
                          for tid, slot in conflicts)
        st.warning(tr("More than one match is routed into the same slot ({spots}) — only the "
                      "most recently saved one will actually land there. Fix that below.",
                      spots=spots))

    rounds = sorted({m["round_no"] for m in matches})
    for rno in rounds:
        round_matches = sorted((m for m in matches if m["round_no"] == rno),
                               key=lambda x: x["match_no"])
        later_matches = [m for m in matches if m["round_no"] > rno]
        st.markdown("##### " + tr("Round {n}", n=rno))
        for m in round_matches:
            _custom_route_row(ev, m, later_matches)

    st.divider()
    next_round_no = rounds[-1] + 1
    st.markdown("##### " + tr("Add matches to a round"))
    st.caption(tr("Round {next} would be a new round — but you can also add more matches to an "
                  "existing round (like round {last}) if you need another slot for, say, a loser "
                  "who's still playing.", next=next_round_no, last=rounds[-1]))
    c1, c2 = st.columns(2)
    default_target = rounds[-1] if rounds[-1] >= 2 else next_round_no
    target_round = c1.number_input(tr("Round number"), min_value=2, max_value=next_round_no,
                                   value=default_target, key=f"customtargetround_{ev['id']}")
    n = c2.number_input(tr("How many matches to add"), 1, 12, 1,
                        key=f"customcount_{ev['id']}_{int(target_round)}")
    if st.button(tr("Add {n} match(es) to round {r}", n=int(n), r=int(target_round)),
                 key=f"customadd_{ev['id']}_{int(target_round)}"):
        formats.custom_add_round(ev["id"], int(target_round), int(n), actor=ui.admin_name())
        st.rerun()


def _routing_conflicts(matches):
    """Slots that more than one match has been routed into — the last save
    wins, silently, unless we point it out."""
    targets: dict[tuple, int] = {}
    conflicts = set()
    for m in matches:
        for tid, slot in ((m["next_match_id"], m["next_slot"]),
                          (m["loser_next_match_id"], m["loser_next_slot"])):
            if tid and slot:
                key = (tid, slot)
                if key in targets and targets[key] != m["id"]:
                    conflicts.add(key)
                targets[key] = m["id"]
    return conflicts


def _custom_round1(ev, entries):
    if len(entries) < 2:
        ui.empty_state(tr("Need at least two entries before you can build round 1."))
        return
    match_count = len(entries) // 2
    if len(entries) % 2:
        st.caption(tr("{n} entries — one will be left unpaired here; pair up the rest, then give "
                      "the odd one out a bye on the Fixtures page afterward.", n=len(entries)))

    containers = [{"header": tr("Unpaired"), "items": [e["name"] for e in entries]}]
    containers += [{"header": tr("Match {n}", n=i + 1), "items": []} for i in range(match_count)]
    name_to_id = {e["name"]: e["id"] for e in entries}

    st.caption(tr("Drag two entries into the same match to pair them up."))
    result = sort_items(containers, multi_containers=True, direction="horizontal",
                        custom_style=ui.sortable_css(ui.theme_color("terracotta")),
                        key=f"custom_r1_{ev['id']}")

    pairs, incomplete = [], False
    for c in result[1:]:
        ids = [name_to_id[n] for n in c["items"]]
        if len(ids) == 2:
            pairs.append(tuple(ids))
        elif ids:
            incomplete = True

    st.caption(tr("{a} of {b} round-1 matches paired up.", a=len(pairs), b=match_count))
    ready = len(pairs) == match_count and not incomplete
    if st.button(tr("Create round 1"), type="primary", disabled=not ready,
                 key=f"custom_r1_create_{ev['id']}"):
        try:
            formats.custom_build_round1(ev["id"], pairs, actor=ui.admin_name())
            st.success(tr("Round 1 created — route each match's winner (and loser, if you want) "
                          "below, or add round 2 once you're ready."))
            st.rerun()
        except models.RuleError as e:
            st.error(str(e))


def _custom_route_row(ev, m, later_matches):
    emap = models.entries_map(ev["id"])
    a = emap.get(m["entry_a_id"], {}).get("name", tr("TBD"))
    b = emap.get(m["entry_b_id"], {}).get("name", tr("TBD"))
    badge = ""
    if m["status"] == STATUS_LIVE:
        badge = " · 🔴 " + tr("live")
    elif m["status"] in (STATUS_DONE, STATUS_BYE):
        winner = emap.get(m["winner_entry_id"], {}).get("name", "?")
        badge = " · " + tr("done — {w} won", w=winner)
    st.markdown(f"**{tr('Match {n}', n=m['match_no'])}** · {a} {tr('vs')} {b}{badge}")

    if not later_matches:
        st.caption(tr("Add a later round below, then come back here to route this match."))
        return

    options = ["__none__"]
    lookup: dict[str, tuple[int, str]] = {}
    for lm in sorted(later_matches, key=lambda x: (x["round_no"], x["match_no"])):
        for slot in ("A", "B"):
            label = f"R{lm['round_no']} · Match {lm['match_no']} · slot {slot}"
            options.append(label)
            lookup[label] = (lm["id"], slot)

    def show(opt):
        if opt == "__none__":
            return tr("— not set —")
        r, mm, sl = opt.split(" · ")
        return tr("R{r} · Match {m} · slot {s}", r=r[1:], m=mm.split()[-1], s=sl.split()[-1])

    def cur_label(target_id, target_slot):
        for label, (mid, slot) in lookup.items():
            if mid == target_id and slot == target_slot:
                return label
        return options[0]

    c1, c2 = st.columns(2)
    win_label = c1.selectbox(tr("Winner advances to"), options, format_func=show,
                             index=options.index(cur_label(m["next_match_id"], m["next_slot"])),
                             key=f"win_{m['id']}")
    lose_label = c2.selectbox(tr("Loser advances to"), options, format_func=show,
                              index=options.index(cur_label(m["loser_next_match_id"],
                                                            m["loser_next_slot"])),
                              key=f"lose_{m['id']}")

    win_to = lookup.get(win_label)
    lose_to = lookup.get(lose_label)
    cur_win = (m["next_match_id"], m["next_slot"]) if m["next_match_id"] else None
    cur_lose = (m["loser_next_match_id"], m["loser_next_slot"]) if m["loser_next_match_id"] else None
    if (win_to, lose_to) != (cur_win, cur_lose):
        if st.button(tr("Save routing"), key=f"save_route_{m['id']}"):
            formats.custom_wire(m["id"], winner_to=win_to, loser_to=lose_to, actor=ui.admin_name())
            st.rerun()


def _pool_setup(ev, entries):
    st.caption(tr("The draw already happened outside the app — drag each entry into the pool "
                  "it was drawn into. Nothing here is computed for you."))
    max_n = min(len(POOL_NAMES), max(1, len(entries) // 2))
    default_n = min(len({e["pool"] for e in entries if e["pool"]}) or int(ev["pool_count"] or 2), max_n)
    c1, c2 = st.columns([1, 3])
    n = c1.number_input(tr("Pools"), 1, max_n, default_n, key=f"poolcount_{ev['id']}")
    letters = POOL_NAMES[:int(n)]

    by_letter: dict[str, list[str]] = {letter: [] for letter in letters}
    unassigned = []
    for e in entries:
        if e["pool"] in letters:
            by_letter[e["pool"]].append(e["name"])
        else:
            unassigned.append(e["name"])
    name_to_id = {e["name"]: e["id"] for e in entries}

    header_to_letter = {tr("Pool {p}", p=letter): letter for letter in letters}
    containers = [{"header": tr("Unassigned"), "items": unassigned}]
    containers += [{"header": tr("Pool {p}", p=letter), "items": by_letter[letter]}
                   for letter in letters]

    result = sort_items(containers, multi_containers=True, direction="horizontal",
                        custom_style=ui.sortable_css(ui.theme_color("terracotta")),
                        key=f"pools_{ev['id']}_{int(n)}")

    # persist any change immediately — dragging is the save action
    changed = 0
    for container in result[1:]:
        letter = header_to_letter.get(container["header"])
        for name in container["items"]:
            eid = name_to_id[name]
            cur = next(e for e in entries if e["id"] == eid)
            if cur["pool"] != letter:
                models.set_entry_pool(eid, letter, actor=ui.admin_name())
                changed += 1
    for name in result[0]["items"]:
        eid = name_to_id[name]
        cur = next(e for e in entries if e["id"] == eid)
        if cur["pool"] is not None:
            models.set_entry_pool(eid, None, actor=ui.admin_name())
            changed += 1
    if changed:
        st.rerun()

    counts = ", ".join(tr("Pool {p}: {n}", p=letter, n=len(by_letter[letter])) for letter in letters)
    st.caption(counts + (tr(" · {n} unassigned", n=len(unassigned)) if unassigned else ""))
    if unassigned:
        st.warning(tr("{n} entry(ies) not yet assigned to a pool.", n=len(unassigned)))


def _seed_setup(ev, entries, method):
    is_pool = ev["format"] == "pool_playoff"
    if method == "random":
        st.caption(tr("Shuffles every entry into a fresh random order, ignoring any seed numbers — "
                      "pools are then filled by snaking down that order.") if is_pool else
                   tr("Shuffles every entry into a fresh random order, ignoring any seed numbers."))
        if st.button(tr("🎲 Shuffle order"), key=f"shuffle_{ev['id']}"):
            ids = [e["id"] for e in entries]
            random.shuffle(ids)
            models.set_seed_order(ev["id"], ids, actor=ui.admin_name())
            st.rerun()
    elif method == "manual":
        st.caption(tr("The draw already happened outside the app (names pulled from a hat, a "
                      "printed sheet, etc). Drag entries into that exact order, then click "
                      "**Record this order** below — even if the list already looks right, "
                      "nothing is saved until you do."))
    else:
        st.caption(tr("Entries with a seed are ranked first; anyone else fills the remaining "
                      "positions at random when you generate the draw, then pools are filled by "
                      "snaking down that order.") if is_pool else
                   tr("Entries with a seed are ranked first; anyone else fills the remaining "
                      "positions at random when you generate the draw."))

    st.caption(tr("Drag to set the order — top is position 1."))
    ordered = sorted(entries, key=lambda e: (e["seed"] is None, e["seed"] or 0, e["name"]))
    names = [e["name"] for e in ordered]
    name_to_id = {e["name"]: e["id"] for e in entries}

    result = sort_items(names, direction="vertical",
                        custom_style=ui.sortable_css(ui.theme_color("olive")), key=f"seed_{ev['id']}")
    new_order = [name_to_id[n] for n in result]
    cur_order = [e["id"] for e in ordered]
    if new_order != cur_order:
        models.set_seed_order(ev["id"], new_order, actor=ui.admin_name())
        st.rerun()

    if method == "manual":
        missing = [e["name"] for e in entries if not e["seed"]]
        if missing:
            st.warning(tr("Nothing recorded yet — the list above is only a preview until you "
                          "save it, even if the order already looks correct."))
            if st.button(tr("✅ Record this order"), type="primary", key=f"record_order_{ev['id']}"):
                models.set_seed_order(ev["id"], new_order, actor=ui.admin_name())
                st.success(tr("Recorded."))
                st.rerun()
        else:
            st.caption(tr("✅ Recorded — every entry has a position."))


def _draw_view(ev, emap, games):
    matches = models.list_matches(ev["id"])
    if not matches:
        n = len(models.list_entries(ev["id"]))
        ui.empty_state(tr("No draw yet ({n} entries confirmed).", n=n))
        if ui.is_admin():
            st.caption(tr("Set up and generate the draw in Players & entries → Event entries."))
        return
    if draw_method(ev["id"]) == "custom":
        # A hand-built bracket can have any shape at all — round columns with
        # whatever matches are actually in each round is the one view that's
        # always correct for it, regardless of the event's nominal format.
        ui.render_bracket(matches, emap, games)
        return
    fmt = ev["format"]

    if fmt in ("single_elim",):
        main = [m for m in matches if m["round_label"] != "3rd place"]
        ui.render_bracket(main, emap, games)
        third = [m for m in matches if m["round_label"] == "3rd place"]
        if third:
            ui.render_bracket(third, emap, games, title=tr("3rd place"))

    elif fmt == "double_elim":
        wb = [m for m in matches if m["stage"] == STAGE_WB]
        lb = [m for m in matches if m["stage"] == STAGE_LB]
        gf = [m for m in matches if m["stage"] == STAGE_GF]
        ui.render_bracket(wb, emap, games, title=tr("Winners bracket"))
        ui.render_bracket(lb, emap, games, title=tr("Losers bracket"))
        ui.render_bracket(gf, emap, games, title=tr("Grand final"))
        if len(gf) > 1:
            st.caption(tr("The losers-bracket survivor won the first grand final, so a deciding "
                          "match was created — both sides carry one loss."))

    elif fmt == "pool_playoff":
        po = [m for m in matches if m["stage"] == STAGE_PLAYOFF]
        tables = standings.pool_standings(ev["id"])
        st.markdown("#### " + tr("Pools"))
        cols = st.columns(min(3, max(1, len(tables))))
        for i, (letter, rows) in enumerate(tables.items()):
            with cols[i % len(cols)]:
                st.markdown(f"**{tr('Pool {p}', p=letter)}**")
                st.dataframe(ui.standings_frame(rows), hide_index=True, width="stretch")
        if po:
            st.markdown("#### " + tr("Playoffs"))
            main = [m for m in po if m["round_label"] != "Playoff 3rd place"]
            ui.render_bracket(main, emap, games)
            third = [m for m in po if m["round_label"] == "Playoff 3rd place"]
            if third:
                ui.render_bracket(third, emap, games, title=tr("3rd place"))
        else:
            st.info(tr("Playoff bracket appears once every pool match is finished."))

    else:   # round robin and Swiss are grids, not trees
        rounds: dict[int, list] = {}
        for m in matches:
            rounds.setdefault(m["round_no"], []).append(m)
        for rno in sorted(rounds):
            ms = sorted(rounds[rno], key=lambda m: m["match_no"])
            st.markdown(f"**{i18n.round_label(ms[0].get('round_label')) or tr('Round {n}', n=rno)}**")
            cols = st.columns(2)
            for i, m in enumerate(ms):
                with cols[i % 2]:
                    if m["status"] in ("done", "bye"):
                        ui.render_result(m, emap, games.get(m["id"], []))
                    elif m["status"] == "live":
                        ui.render_live_match(m, emap, games.get(m["id"], []))
                    else:
                        ui.render_upcoming(m, emap)


def render():
    t = ui.need_tournament()
    if not t:
        return
    ui.masthead(tr("Draws and standings"), t["name"])

    events = models.list_events(t["id"])
    if not events:
        ui.empty_state(tr("No events yet."))
        return

    tabs = st.tabs([i18n.cat(e["category"]) for e in events] + [tr("Player leaderboard")])

    for tab, ev in zip(tabs, events):
        with tab:
            st.caption(f"{i18n.fmt(ev['format'])} · {i18n.preset_label(models.scoring_rule(ev))} · "
                       f"{tr('best of {n}', n=ev['best_of'])} · {i18n.status(ev['status'])}")
            emap = models.entries_map(ev["id"])
            games = models.games_for_event(ev["id"])

            sub1, sub2 = st.tabs([tr("Standings"), tr("Draw")])
            with sub1:
                rows = standings.event_table(ev["id"])
                if not rows:
                    ui.empty_state(tr("No entries yet."))
                else:
                    if ev["status"] == "complete":
                        podium = rows[:3]
                        cols = st.columns(3)
                        for c, r, label in zip(cols, podium,
                                               [tr("Champion"), tr("Runner-up"), tr("Third")]):
                            c.metric(label, r["name"], f"{r['wins']}-{r['losses']}")
                    st.dataframe(ui.standings_frame(rows, swiss=ev["format"] == "swiss"),
                                 hide_index=True, width="stretch")
                    if ev["format"] == "swiss":
                        st.caption(tr("Buchholz is the combined win total of the opponents each "
                                      "entry actually faced — it separates equal records by "
                                      "strength of schedule."))
                    else:
                        st.caption(tr("Ties break on head-to-head first, then game differential, "
                                      "then point differential."))
            with sub2:
                _draw_view(ev, emap, games)

    with tabs[-1]:
        st.caption(tr("Every individual across every event they entered — doubles results count "
                      "for both partners."))
        rows = standings.player_leaderboard(t["id"])
        if not rows:
            ui.empty_state(tr("No results yet."))
        else:
            st.dataframe(
                [{"#": r["rank"], tr("Player"): r["player"], tr("Club"): r["club"],
                  tr("Events"): r["events"], tr("P"): r["played"], tr("W"): r["wins"],
                  tr("L"): r["losses"], tr("Win %"): round(r["win_pct"] * 100, 1),
                  tr("Diff"): r["point_diff"]}
                 for r in rows],
                hide_index=True, width="stretch")
