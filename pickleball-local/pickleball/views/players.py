"""Player roster and per-event entry lists — and the draw for each event,
set up and generated right next to its entries."""

from __future__ import annotations

import streamlit as st
from streamlit_sortables import sort_items

from tourney import formats, i18n, models
from tourney.constants import GENDER_RULE, TEAM_SIZE
from tourney.i18n import tr
from views import brackets, ui

GENDERS = ["M", "F", "—"]


def _gender_label(g):
    return {"M": tr("Male"), "F": tr("Female"), "—": "—"}.get(g, g)


def _roster_tab(t):
    players = models.list_players(t["id"])
    st.caption(tr("{n} players registered. Names are shared across every event, so the same "
                  "person can enter singles and doubles.", n=len(players)))

    c1, c2 = st.columns([3, 2])
    with c1:
        with st.form("add_player", clear_on_submit=True):
            st.markdown("**" + tr("Add one player") + "**")
            a, b, c = st.columns([3, 1, 2])
            name = a.text_input(tr("Name"), placeholder="Nguyen Van A")
            gender = b.selectbox(tr("Gender"), GENDERS, format_func=_gender_label)
            club = c.text_input(tr("Club"), placeholder=tr("Optional"))
            if st.form_submit_button(tr("Add player"), type="primary"):
                try:
                    models.add_player(t["id"], name,
                                      gender=None if gender == "—" else gender,
                                      club=club, actor=ui.admin_name())
                    st.success(tr("{name} added.", name=name))
                    st.rerun()
                except models.RuleError as e:
                    st.error(str(e))

    with c2:
        with st.form("bulk_players", clear_on_submit=True):
            st.markdown("**" + tr("Paste a list") + "**")
            st.caption(tr("One per line: `Name, M, Club` — gender (M/F) and club optional."))
            blob = st.text_area(tr("Players"), height=120, label_visibility="collapsed",
                                placeholder="Tran Thi B, F, Riverside\nLe Van C, M")
            if st.form_submit_button(tr("Add all")):
                added = 0
                for line in blob.splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if not parts or not parts[0]:
                        continue
                    g = parts[1].upper()[:1] if len(parts) > 1 and parts[1] else None
                    models.add_player(t["id"], parts[0],
                                      gender=g if g in ("M", "F") else None,
                                      club=parts[2] if len(parts) > 2 else "",
                                      actor=ui.admin_name())
                    added += 1
                st.success(tr("{n} name(s) processed. Duplicates were merged.", n=added))
                st.rerun()

    st.divider()
    if not players:
        ui.empty_state(tr("No players yet."))
        return

    st.markdown("**" + tr("Roster") + "**")
    col_name, col_gender, col_club, col_rating = tr("Name"), tr("Gender"), tr("Club"), tr("Rating")
    edited = st.data_editor(
        [{"id": p["id"], col_name: p["name"], col_gender: p["gender"] or "—",
          col_club: p["club"] or "", col_rating: p["rating"]} for p in players],
        column_config={
            "id": None,
            col_gender: st.column_config.SelectboxColumn(options=GENDERS),
            col_rating: st.column_config.NumberColumn(format="%.2f", min_value=0.0, max_value=8.0),
        },
        hide_index=True, width="stretch", key="roster_editor")

    c1, c2 = st.columns([1, 3])
    if c1.button(tr("Save roster edits")):
        by_id = {p["id"]: p for p in players}
        n = 0
        try:
            for row in edited:
                p = by_id.get(row["id"])
                if not p:
                    continue
                new = {"name": " ".join(str(row[col_name] or "").split()),
                       "gender": None if row[col_gender] == "—" else row[col_gender],
                       "club": row[col_club], "rating": row[col_rating]}
                if any(new[k] != p[k] for k in new):
                    models.update_player(p["id"], new, actor=ui.admin_name())
                    n += 1
            st.success(tr("{n} player(s) updated.", n=n))
            st.rerun()
        except models.RuleError as e:
            st.error(str(e))

    with c2.expander(tr("Remove a player")):
        pick = st.selectbox(tr("Player"), [p["id"] for p in players],
                            format_func=lambda i: next(p["name"] for p in players if p["id"] == i),
                            key="del_player")
        if st.button(tr("Remove")):
            try:
                models.delete_player(pick, actor=ui.admin_name())
                st.success(tr("Removed."))
                st.rerun()
            except models.RuleError as e:
                st.error(str(e))


def _entries_tab(t):
    events = models.list_events(t["id"])
    if not events:
        ui.empty_state(tr("Add an event on the Setup page first."))
        return
    eid = ui.event_picker(t["id"], key="entry_event")
    ev = models.get_event(eid)
    category = ev["category"]
    team_size = TEAM_SIZE[category]
    players = models.list_players(t["id"])
    if not players:
        ui.empty_state(tr("Add players to the roster first."))
        return

    entries = models.list_entries(eid)
    taken = set()
    for e in entries:
        taken.update(filter(None, (e["player1_id"], e["player2_id"])))
    pool = [p for p in models.eligible_players(category, 0, players) if p["id"] not in taken]
    if category == "XD":
        pool += [p for p in models.eligible_players(category, 1, players) if p["id"] not in taken]
    name_by_id = {p["id"]: p["name"] for p in pool}
    id_by_name = {p["name"]: p["id"] for p in pool}
    no_gender = [p for p in players if p["id"] not in taken and not p.get("gender")]

    has_draw = bool(models.list_matches(eid))
    if has_draw:
        st.warning(tr("This event already has a draw. New entries will not appear in it — clear "
                      "the draw below if you need to re-seed."))

    st.markdown("**" + tr("Build entries for {event}", event=i18n.cat(category)) + "**")
    rule = GENDER_RULE.get(category)
    if rule and no_gender:
        names = ", ".join(p["name"] for p in no_gender[:6])
        more = "…" if len(no_gender) > 6 else ""
        st.caption(tr("{n} player(s) without a gender set do not appear below ({names}{more}) — "
                      "set their gender on the Roster tab.",
                      n=len(no_gender), names=names, more=more))

    if not pool:
        st.caption(tr("No eligible unentered players left for this event."))
    else:
        ver_key, ids_key, auto_key = (f"bld_ver_{eid}", f"bld_ids_{eid}", f"bld_auto_{eid}")

        st.caption(tr("{n} eligible unentered players available. Team size: {size}.",
                      n=len(pool), size=team_size))
        chosen_ids = st.multiselect(
            tr("Players participating — pick exactly who is in this event"),
            options=[p["id"] for p in pool], format_func=lambda i: name_by_id[i],
            placeholder=tr("Choose players"), key=f"pick_{eid}")
        n_chosen = len(chosen_ids)
        ok_count = n_chosen >= team_size and n_chosen % team_size == 0
        if n_chosen and not ok_count:
            st.caption(tr("{n} selected — doesn't divide evenly into teams of {size}. Pick a "
                          "multiple of {size}.", n=n_chosen, size=team_size))
        if st.button(tr("Create team zones"), type="primary", key=f"gen_zones_{eid}",
                     disabled=not ok_count):
            st.session_state[ver_key] = st.session_state.get(ver_key, 0) + 1
            st.session_state[ids_key] = chosen_ids
            st.session_state[auto_key] = team_size == 1 and n_chosen == len(pool)

        if ids_key in st.session_state:
            _team_builder(eid, ev, category, team_size, name_by_id, id_by_name,
                          st.session_state[ids_key], st.session_state.get(ver_key, 0),
                          st.session_state.get(auto_key, False))

    st.divider()
    st.markdown("**" + tr("{n} entries", n=len(entries)) + "**")
    if not entries:
        ui.empty_state(tr("No entries in this event yet."))
        return

    col_entry, col_seed, col_pool, col_status = tr("Entry"), tr("Seed"), tr("Pool"), tr("Status")
    edited = st.data_editor(
        [{"id": e["id"], col_entry: e["name"], col_seed: e["seed"] or 0,
          col_pool: e["pool"] or "", col_status: i18n.status(e["status"])} for e in entries],
        column_config={
            "id": None,
            col_entry: st.column_config.TextColumn(disabled=True),
            col_pool: st.column_config.TextColumn(disabled=True),
            col_status: st.column_config.TextColumn(disabled=True),
            col_seed: st.column_config.NumberColumn(min_value=0, max_value=128, step=1),
        },
        hide_index=True, width="stretch", key="entries_editor")

    c1, c2, c3, c4 = st.columns(4)
    if c1.button(tr("Save seeds")):
        by_id = {e["id"]: e for e in entries}
        n = 0
        for row in edited:
            want = int(row[col_seed]) or None
            if by_id[row["id"]]["seed"] != want:
                models.set_seed(row["id"], want, actor=ui.admin_name())
                n += 1
        st.success(tr("{n} seed(s) updated.", n=n))
        st.rerun()

    names_by_pid = {p["id"]: p["name"] for p in players}
    with c2.expander(tr("🔄 Substitute a player")):
        st.caption(tr("A last-minute withdrawal — swap one player out for another on an existing "
                      "team. The team keeps its seed, its pool, and its exact spot in the draw; "
                      "only who's playing changes."))
        team_pick = st.selectbox(tr("Team"), [e["id"] for e in entries],
                                 format_func=lambda i: next(e["name"] for e in entries if e["id"] == i),
                                 key="sub_entry")
        entry = next(e for e in entries if e["id"] == team_pick)
        slots = [("player1_id", entry["player1_id"])]
        if entry["player2_id"]:
            slots.append(("player2_id", entry["player2_id"]))
        out_field, out_pid = st.selectbox(
            tr("Who's leaving"), slots, format_func=lambda s: names_by_pid.get(s[1], "?"),
            key="sub_out")
        slot_idx = 0 if out_field == "player1_id" else 1
        subs = models.eligible_substitutes(team_pick, slot_idx)
        if not subs:
            st.caption(tr("No eligible replacement in the roster — add one on the Roster tab "
                          "first, then come back here."))
        else:
            in_pid = st.selectbox(tr("Who's coming in"), [p["id"] for p in subs],
                                  format_func=lambda i: names_by_pid.get(i, "?"), key="sub_in")
            if st.button(tr("Substitute now"), type="primary", key="sub_go"):
                try:
                    new_name = models.substitute_player(team_pick, out_pid, in_pid,
                                                        actor=ui.admin_name())
                    st.success(tr("Done — now {name}.", name=new_name))
                    st.rerun()
                except models.RuleError as e:
                    st.error(str(e))

    with c3.expander(tr("Withdraw an entry")):
        st.caption(tr("Keeps completed results and concedes everything still to play."))
        pick = st.selectbox(tr("Entry"), [e["id"] for e in entries],
                            format_func=lambda i: next(e["name"] for e in entries if e["id"] == i),
                            key="wd_entry")
        if st.button(tr("Withdraw")):
            models.withdraw_entry(pick, actor=ui.admin_name())
            st.success(tr("Withdrawn."))
            st.rerun()

    with c4.expander(tr("Delete an entry")):
        st.caption(tr("Only possible before they have played."))
        pick = st.selectbox(tr("Entry"), [e["id"] for e in entries],
                            format_func=lambda i: next(e["name"] for e in entries if e["id"] == i),
                            key="del_entry")
        if st.button(tr("Delete entry")):
            try:
                models.delete_entry(pick, actor=ui.admin_name())
                st.success(tr("Deleted."))
                st.rerun()
            except models.RuleError as e:
                st.error(str(e))

    st.divider()
    _draw_section(t, eid, ev, entries)


def _team_builder(eid, ev, category, team_size, name_by_id, id_by_name,
                  chosen_ids, version, auto_singles):
    """Drag players from the tray onto a team zone. Singles where every
    eligible player is participating skips the drag step entirely — there's
    only one way to arrange it, so each player becomes their own entry."""
    if auto_singles:
        st.info(tr("All {n} eligible players are in — each becomes its own entry, no need to drag.",
                   n=len(chosen_ids)))
        for pid in chosen_ids:
            st.markdown(f'<span class="pk-tag">{name_by_id[pid]}</span>', unsafe_allow_html=True)
        if st.button(tr("Confirm entries"), type="primary", key=f"confirm_auto_{eid}_{version}"):
            n = 0
            for pid in chosen_ids:
                try:
                    models.add_entry(eid, pid, None, actor=ui.admin_name())
                    n += 1
                except models.RuleError:
                    pass
            st.success(tr("{n} entries confirmed.", n=n))
            for k in (f"bld_ver_{eid}", f"bld_ids_{eid}", f"bld_auto_{eid}"):
                st.session_state.pop(k, None)
            st.rerun()
        return

    team_count = len(chosen_ids) // team_size
    noun = tr("Entry") if team_size == 1 else tr("Team")
    containers = [{"header": tr("Unplaced"), "items": [name_by_id[i] for i in chosen_ids]}]
    containers += [{"header": f"{noun} {i + 1}", "items": []} for i in range(team_count)]

    st.caption(tr("Drag a player onto a zone to place them — {n} zone(s) of {size}.",
                  n=team_count, size=team_size))
    result = sort_items(containers, multi_containers=True, direction="horizontal",
                        custom_style=ui.sortable_css(ui.theme_color("terracotta")),
                        key=f"sort_{eid}_{version}")

    unplaced = result[0]["items"]
    zones = result[1:]
    complete = 0
    issues = []
    zone_members: list[list[int]] = []
    for c in zones:
        member_ids = [id_by_name[n] for n in c["items"]]
        zone_members.append(member_ids)
        if not member_ids:
            continue
        if len(member_ids) != team_size:
            issues.append(tr("{zone}: needs exactly {size}, has {n}",
                             zone=c["header"], size=team_size, n=len(member_ids)))
            continue
        ok, complaint = models.team_gender_ok(category, member_ids)
        if ok:
            complete += 1
        else:
            issues.append(f"{c['header']}: {complaint or ''}")

    st.markdown("**" + tr("{a} of {b} complete", a=complete, b=team_count) + "**"
                + (tr(" · {n} unplaced", n=len(unplaced)) if unplaced else ""))
    for msg in issues:
        st.caption(f"⚠ {msg}")

    ready = complete == team_count and not unplaced
    if st.button(tr("Confirm entries"), type="primary", disabled=not ready,
                 key=f"confirm_{eid}_{version}"):
        n = 0
        for member_ids in zone_members:
            try:
                a = member_ids[0]
                b = member_ids[1] if len(member_ids) > 1 else None
                models.add_entry(eid, a, b, actor=ui.admin_name())
                n += 1
            except models.RuleError as e:
                st.error(str(e))
        if n:
            st.success(tr("{n} entry(ies) confirmed.", n=n))
            for k in (f"bld_ver_{eid}", f"bld_ids_{eid}", f"bld_auto_{eid}"):
                st.session_state.pop(k, None)
            st.rerun()


def _draw_section(t, eid, ev, entries):
    """Everything about this event's draw, in one place: how it's ordered
    (seed / random / manual / custom), dragging entries into order or pools,
    the format's own options, and the Generate button — then, once the draw
    exists, its progress, the custom bracket builder, and Clear."""
    matches = models.list_matches(eid)
    st.markdown("### " + tr("Draw"))

    if not matches:
        st.markdown("**" + tr("Set up the draw for {event}", event=i18n.cat(ev["category"])) + "**")
        if len(entries) < 2:
            st.caption(tr("Add at least two entries above before building the draw."))
            return
        method = brackets.draw_setup(ev, entries)
        if method == "custom":
            return       # the custom builder above creates the matches itself
        st.divider()
        kwargs = {}
        if ev["format"] == "pool_playoff":
            if method == "manual":
                pools_set = {e["pool"] for e in models.list_entries(eid) if e["pool"]}
                if not (pools_set and all(e["pool"] for e in models.list_entries(eid))):
                    st.warning(tr("Not every entry has a pool yet — drag them into pools above."))
            else:
                pc_max = min(12, max(1, len(entries) // 2))
                pc_default = min(int(ev["pool_count"] or 2), pc_max)
                kwargs["pool_count"] = st.number_input(
                    tr("Pools"), 1, pc_max, pc_default, key=f"pc_{ev['id']}")
        if ev["format"] == "single_elim":
            kwargs["third_place"] = st.checkbox(
                tr("Include a 3rd place match"), value=True, key=f"tp_{ev['id']}")
        if st.button(tr("Generate draw"), type="primary", key=f"gen_{ev['id']}"):
            try:
                formats.generate_draw(eid, actor=ui.admin_name(), method=method, **kwargs)
                st.success(tr("Draw created."))
                st.session_state.pop(f"draw_method_{eid}", None)
                st.rerun()
            except models.RuleError as e:
                st.error(str(e))
        return

    played = sum(1 for m in matches if m["status"] in ("done", "bye"))
    st.progress(played / len(matches),
                text=tr("{a} of {b} matches played", a=played, b=len(matches)))
    st.caption(tr("Draw method: {m}. Enter results on the Scoring desk page; the bracket is on "
                  "Draws & standings.", m=brackets.method_label(brackets.draw_method(eid))))
    if brackets.draw_method(eid) == "custom":
        with st.expander(tr("Continue building the bracket"), expanded=False):
            brackets.custom_builder(ev, models.list_entries(eid))
    if st.button(tr("Clear draw and start over"), key=f"clr_{ev['id']}"):
        st.session_state[f"confirm_clr_{ev['id']}"] = True
    if st.session_state.get(f"confirm_clr_{ev['id']}"):
        st.warning(tr("This deletes every match and score in this event. Entries stay."))
        if st.button(tr("Yes, clear it"), key=f"clr2_{ev['id']}", type="primary"):
            models.clear_draw(eid, actor=ui.admin_name())
            st.session_state.pop(f"confirm_clr_{ev['id']}")
            st.rerun()


def render():
    t = ui.need_tournament()
    if not t:
        return
    ui.masthead(tr("Players and entries"), t["name"])
    if not ui.require_admin(tr("manage players")):
        return
    tab1, tab2 = st.tabs([tr("Roster"), tr("Event entries")])
    with tab1:
        _roster_tab(t)
    with tab2:
        _entries_tab(t)
