"""Domain objects and the rules that move a result through a draw."""

from __future__ import annotations

import json

from . import db, i18n, rules
from .i18n import cat, tr
from .constants import (
    CATEGORIES, GENDER_RULE, OPEN_STATUSES, SCORING_PRESETS, STAGE_GF, STAGE_LB, STAGE_MAIN,
    STATUS_BYE, STATUS_DONE, STATUS_LIVE, STATUS_PENDING, STATUS_VOID, TEAM_SIZE,
)


class ConflictError(Exception):
    """Another admin changed this match first."""


class RuleError(Exception):
    """The requested change would break the draw."""


# --------------------------------------------------------------------------
# Tournaments
# --------------------------------------------------------------------------

def create_tournament(name, venue="", start_date=None, end_date=None, notes="",
                      actor=None, is_quick=False) -> int:
    tid = db.insert("tournaments", {
        "name": name.strip(), "venue": venue.strip(), "start_date": start_date,
        "end_date": end_date, "status": "setup", "notes": notes, "is_quick": int(is_quick),
        "created_at": db.now(), "created_by": actor,
    })
    db.log(actor, tid, "tournament", tid, "create", name)
    return tid


def list_tournaments(include_quick=False) -> list[dict]:
    if include_quick:
        return db.query("SELECT * FROM tournaments ORDER BY COALESCE(start_date, created_at) DESC, id DESC")
    return db.query(
        "SELECT * FROM tournaments WHERE is_quick = 0 "
        "ORDER BY COALESCE(start_date, created_at) DESC, id DESC")


def get_tournament(tid: int) -> dict | None:
    return db.query_one("SELECT * FROM tournaments WHERE id = ?", (tid,))


def list_courts(tournament_id: int) -> list[dict]:
    return db.query(
        "SELECT * FROM courts WHERE tournament_id = ? ORDER BY sort_order, id", (tournament_id,))


def add_court(tournament_id: int, name: str, actor=None) -> int:
    name = " ".join(name.split())
    if not name:
        raise RuleError(tr("Give the court a name."))
    dupe = db.query_one(
        "SELECT id FROM courts WHERE tournament_id = ? AND LOWER(name) = LOWER(?)",
        (tournament_id, name))
    if dupe:
        return dupe["id"]
    order = len(list_courts(tournament_id))
    cid = db.insert("courts", {
        "tournament_id": tournament_id, "name": name, "status": "open",
        "sort_order": order, "created_at": db.now()})
    db.log(actor, tournament_id, "court", cid, "create", name)
    return cid


def set_court_status(court_id: int, status: str, actor=None):
    db.update("courts", court_id, {"status": status})
    db.log(actor, None, "court", court_id, "status", status)


def delete_court(court_id: int, actor=None):
    c = db.query_one("SELECT * FROM courts WHERE id = ?", (court_id,))
    if not c:
        return
    live = db.query_one(
        "SELECT m.id FROM matches m JOIN events e ON e.id = m.event_id "
        "WHERE e.tournament_id = ? AND m.court = ? AND m.status = ?",
        (c["tournament_id"], c["name"], STATUS_LIVE))
    if live:
        raise RuleError(tr("A match is on this court right now."))
    db.execute("DELETE FROM courts WHERE id = ?", (court_id,))
    db.log(actor, c["tournament_id"], "court", court_id, "delete", c["name"])


def delete_tournament(tid: int, actor=None):
    db.execute("DELETE FROM courts WHERE tournament_id = ?", (tid,))
    # Explicit cascade so it behaves the same on SQLite and Postgres.
    db.execute("DELETE FROM rallies WHERE match_id IN (SELECT m.id FROM matches m "
               "JOIN events e ON e.id = m.event_id WHERE e.tournament_id = ?)", (tid,))
    db.execute("DELETE FROM games WHERE match_id IN (SELECT m.id FROM matches m "
               "JOIN events e ON e.id = m.event_id WHERE e.tournament_id = ?)", (tid,))
    db.execute("DELETE FROM matches WHERE event_id IN (SELECT id FROM events WHERE tournament_id = ?)", (tid,))
    db.execute("DELETE FROM entries WHERE event_id IN (SELECT id FROM events WHERE tournament_id = ?)", (tid,))
    db.execute("DELETE FROM events WHERE tournament_id = ?", (tid,))
    db.execute("DELETE FROM players WHERE tournament_id = ?", (tid,))
    db.execute("DELETE FROM tournaments WHERE id = ?", (tid,))
    db.log(actor, tid, "tournament", tid, "delete", "")


# --------------------------------------------------------------------------
# Quick matches — one-off games that aren't part of any tournament
# --------------------------------------------------------------------------
# Every quick match gets its own tiny event (so concurrent quick matches
# never share a draw or a standings table) tucked inside one hidden
# tournament, which keeps every existing scoring/audit/live code path
# working unchanged instead of forking a parallel data model.

QUICK_TOURNAMENT_NAME = "Quick matches"


def get_or_create_quick_tournament(actor=None) -> int:
    row = db.query_one("SELECT id FROM tournaments WHERE is_quick = 1 LIMIT 1")
    if row:
        return row["id"]
    return create_tournament(
        QUICK_TOURNAMENT_NAME,
        notes="Auto-created holder for matches started outside any tournament.",
        actor=actor, is_quick=True)


def start_quick_match(name_a: str, name_b: str, scoring="11_rally_2", best_of=3,
                      actor=None, scoring_system=rules.SIDE_OUT,
                      partner_a: str = "", partner_b: str = "") -> dict:
    """Creates a standalone, ready-to-score match with no tournament setup —
    just names, a scoring format, and a court. Give both partners for a
    doubles quick match (stored as "Name / Partner"). Returns the new match."""
    name_a, name_b = " ".join(name_a.split()), " ".join(name_b.split())
    partner_a, partner_b = " ".join((partner_a or "").split()), " ".join((partner_b or "").split())
    if not name_a or not name_b:
        raise RuleError(tr("Both names are required."))
    if bool(partner_a) != bool(partner_b):
        raise RuleError(tr("For doubles, give a partner on both sides (or neither for singles)."))
    if partner_a:
        name_a, name_b = f"{name_a} / {partner_a}", f"{name_b} / {partner_b}"
    tid = get_or_create_quick_tournament(actor)
    eid = create_event(tid, "QM", "single_elim", best_of=best_of, scoring=scoring, actor=actor,
                       scoring_system=scoring_system)
    a_id = db.insert("entries", {
        "event_id": eid, "name": name_a, "seed": None, "pool": None,
        "status": "active", "created_at": db.now(), "created_by": actor})
    b_id = db.insert("entries", {
        "event_id": eid, "name": name_b, "seed": None, "pool": None,
        "status": "active", "created_at": db.now(), "created_by": actor})
    mid = create_match(eid, STAGE_MAIN, 1, 1, round_label="Quick Match",
                       entry_a_id=a_id, entry_b_id=b_id, best_of=best_of)
    db.log(actor, tid, "match", mid, "quick_match", f"{name_a} vs {name_b}")
    return get_match(mid)


def list_quick_matches(statuses=None) -> list[dict]:
    tid = get_or_create_quick_tournament()
    matches: list[dict] = []
    for ev in list_events(tid):
        matches.extend(list_matches(ev["id"], statuses=statuses))
    matches.sort(key=lambda m: m["id"], reverse=True)
    return matches


# --------------------------------------------------------------------------
# Events (a category + format pairing inside one tournament)
# --------------------------------------------------------------------------

def create_event(tournament_id, category, fmt, best_of=3, scoring="11_rally_2",
                 swiss_rounds=5, pool_count=2, advance_per_pool=2, gf_reset=True,
                 actor=None, scoring_system=rules.SIDE_OUT) -> int:
    if scoring_system not in rules.SCORING_SYSTEMS:
        raise RuleError(tr("Unknown scoring system {x}", x=scoring_system))
    if category not in CATEGORIES:
        raise RuleError(tr("Unknown category {x}", x=category))
    # "QM" (Quick Match) is exempt from the one-event-per-category rule: every
    # quick match gets its own event so concurrent quick matches never share a
    # draw, but they all share the single hidden quick-matches tournament.
    if category != "QM":
        existing = db.query_one(
            "SELECT id FROM events WHERE tournament_id = ? AND category = ?",
            (tournament_id, category))
        if existing:
            raise RuleError(tr("{event} already exists in this tournament.", event=cat(category)))
    eid = db.insert("events", {
        "tournament_id": tournament_id, "category": category, "format": fmt,
        "status": "setup", "best_of": best_of, "scoring": scoring,
        "swiss_rounds": swiss_rounds, "pool_count": pool_count,
        "advance_per_pool": advance_per_pool, "gf_reset": 1 if gf_reset else 0,
        "scoring_system": scoring_system, "created_at": db.now(),
    })
    db.log(actor, tournament_id, "event", eid, "create", f"{category}/{fmt}")
    return eid


def list_events(tournament_id: int) -> list[dict]:
    return db.query("SELECT * FROM events WHERE tournament_id = ? ORDER BY id", (tournament_id,))


def get_event(eid: int) -> dict | None:
    return db.query_one("SELECT * FROM events WHERE id = ?", (eid,))


def set_draw_method(eid: int, method: str, actor=None):
    """Persisted on the event itself (not just session state) so the choice
    — and, for custom brackets, whether the round-by-round builder should
    stay reachable — survives a reload or a different admin's session."""
    db.update("events", eid, {"draw_method": method})
    db.log(actor, None, "event", eid, "draw_method", method)


def event_label(ev: dict) -> str:
    from . import i18n
    return i18n.category_label(ev["category"], CATEGORIES.get(ev["category"], ev["category"]))


def scoring_rule(ev: dict) -> dict:
    return SCORING_PRESETS.get(ev.get("scoring") or "11_rally_2", SCORING_PRESETS["11_rally_2"])


def scoring_system(ev: dict) -> str:
    sysname = (ev or {}).get("scoring_system") or rules.SIDE_OUT
    return sysname if sysname in rules.SCORING_SYSTEMS else rules.SIDE_OUT


def delete_event(eid: int, actor=None):
    ev = get_event(eid)
    db.execute("DELETE FROM rallies WHERE match_id IN (SELECT id FROM matches WHERE event_id = ?)", (eid,))
    db.execute("DELETE FROM games WHERE match_id IN (SELECT id FROM matches WHERE event_id = ?)", (eid,))
    db.execute("DELETE FROM matches WHERE event_id = ?", (eid,))
    db.execute("DELETE FROM entries WHERE event_id = ?", (eid,))
    db.execute("DELETE FROM events WHERE id = ?", (eid,))
    if ev:
        db.log(actor, ev["tournament_id"], "event", eid, "delete", ev["category"])


def clear_draw(eid: int, actor=None):
    """Wipe every match but keep the entry list."""
    db.execute("DELETE FROM rallies WHERE match_id IN (SELECT id FROM matches WHERE event_id = ?)", (eid,))
    db.execute("DELETE FROM games WHERE match_id IN (SELECT id FROM matches WHERE event_id = ?)", (eid,))
    db.execute("DELETE FROM matches WHERE event_id = ?", (eid,))
    db.execute("UPDATE entries SET pool = NULL WHERE event_id = ?", (eid,))
    db.execute("UPDATE events SET status = 'setup', draw_method = NULL WHERE id = ?", (eid,))
    ev = get_event(eid)
    db.log(actor, ev["tournament_id"] if ev else None, "event", eid, "clear_draw", "")


# --------------------------------------------------------------------------
# Players
# --------------------------------------------------------------------------

def add_player(tournament_id, name, gender=None, club="", rating=None, contact="", actor=None) -> int:
    name = " ".join(name.split())
    if not name:
        raise RuleError(tr("Player name cannot be empty."))
    dupe = db.query_one(
        "SELECT id FROM players WHERE tournament_id = ? AND LOWER(name) = LOWER(?)",
        (tournament_id, name))
    if dupe:
        return dupe["id"]          # idempotent: two admins typing the same name is fine
    pid = db.insert("players", {
        "tournament_id": tournament_id, "name": name, "gender": gender, "club": club,
        "rating": rating, "contact": contact, "created_at": db.now(), "created_by": actor,
    })
    db.log(actor, tournament_id, "player", pid, "create", name)
    return pid


def list_players(tournament_id: int) -> list[dict]:
    return db.query("SELECT * FROM players WHERE tournament_id = ? ORDER BY name", (tournament_id,))


def get_player(pid: int) -> dict | None:
    return db.query_one("SELECT * FROM players WHERE id = ?", (pid,))


def update_player(pid: int, data: dict, actor=None):
    before = get_player(pid)
    data = dict(data)
    if "name" in data:
        data["name"] = " ".join(str(data["name"] or "").split())
        if not data["name"]:
            raise RuleError(tr("Player name cannot be empty."))
        if before and data["name"] != before["name"]:
            _check_name_free(before["tournament_id"], data["name"], pid)
    db.update("players", pid, data)
    p = get_player(pid)
    if p:
        if before and before["name"] != p["name"]:
            _refresh_entries_for_player(pid)
        db.log(actor, p["tournament_id"], "player", pid, "update", str(data))


def _check_name_free(tournament_id, name, pid):
    clash = db.query_one(
        "SELECT id FROM players WHERE tournament_id = ? AND LOWER(name) = LOWER(?) AND id != ?",
        (tournament_id, name, pid))
    if clash:
        raise RuleError(tr("Another player in this tournament is already called {name}.", name=name))


def _refresh_entries_for_player(pid):
    """Entry names are stored ("A / B"), so a renamed player has to be written
    into every entry they're on — in every event. Matches, brackets, standings,
    the live board and the venue display all read the entry name, so this one
    pass updates every one of them."""
    for e in db.query("SELECT * FROM entries WHERE player1_id = ? OR player2_id = ?", (pid, pid)):
        ev = get_event(e["event_id"])
        p1 = get_player(e["player1_id"]) if e["player1_id"] else None
        p2 = get_player(e["player2_id"]) if e["player2_id"] else None
        if ev and p1:
            db.update("entries", e["id"], {"name": entry_display_name(ev, p1, p2)})


def rename_player(pid: int, new_name: str, actor=None) -> str:
    """Correct a registered player's name, right up to (and during) their
    match. The player keeps every entry, seed, pool, draw slot and result —
    only the name changes, everywhere it appears."""
    p = get_player(pid)
    if not p:
        raise RuleError(tr("Player not found."))
    update_player(pid, {"name": new_name}, actor=actor)
    return get_player(pid)["name"]


def rename_entry_names(entry_id: int, names: list[str], actor=None) -> str:
    """For entries with no registered players behind them (quick matches):
    the names are the entry name itself, "A" or "A / B"."""
    e = get_entry(entry_id)
    if not e:
        raise RuleError(tr("Entry not found."))
    clean = [" ".join((n or "").split()) for n in names]
    if not all(clean):
        raise RuleError(tr("Names cannot be empty."))
    new = " / ".join(clean)
    if new != e["name"]:
        db.update("entries", entry_id, {"name": new})
        db.log(actor, None, "entry", entry_id, "rename", f"{e['name']} → {new}")
    return new


def delete_player(pid: int, actor=None):
    used = db.query_one("SELECT id FROM entries WHERE player1_id = ? OR player2_id = ?", (pid, pid))
    if used:
        raise RuleError(tr("This player is on an entry. Remove the entry first."))
    p = get_player(pid)
    db.execute("DELETE FROM players WHERE id = ?", (pid,))
    if p:
        db.log(actor, p["tournament_id"], "player", pid, "delete", p["name"])


# --------------------------------------------------------------------------
# Entries (one player for singles, a pair for doubles)
# --------------------------------------------------------------------------

def entry_display_name(event, p1, p2) -> str:
    if TEAM_SIZE[event["category"]] == 1:
        return p1["name"]
    return f"{p1['name']} / {p2['name']}"


def check_gender(category, p1, p2=None) -> str | None:
    """Returns a warning string, or None. Never hard-blocks — captains swap in
    substitutes at the desk all the time."""
    rule = GENDER_RULE.get(category)
    if not rule:
        return None
    genders = [p1.get("gender"), (p2 or {}).get("gender")][: len(rule)]
    if any(g is None for g in genders):
        return None
    if category == "XD":
        if sorted(g for g in genders) != ["F", "M"]:
            return tr("Mixed Doubles normally pairs one man and one woman.")
        return None
    if any(g != rule[0] for g in genders):
        return tr("{event} normally requires {g} players.", event=cat(category), g=rule[0])
    return None


def slot_gender(category: str, slot_index: int) -> str | None:
    """Required gender ('M'/'F') for a given player slot (0 or 1) in an
    entry for this category, or None if that slot has no restriction."""
    rule = GENDER_RULE.get(category)
    if not rule or slot_index >= len(rule):
        return None
    return rule[slot_index]


def eligible_players(category: str, slot_index: int, players: list[dict]) -> list[dict]:
    """Players who could legally fill this slot — a hard filter, not the
    soft warning `check_gender` gives. A player with no gender recorded
    cannot be confirmed either way, so they are left out; set their gender
    on the Roster tab to make them selectable."""
    need = slot_gender(category, slot_index)
    if not need:
        return players
    return [p for p in players if p.get("gender") == need]


def team_gender_ok(category: str, member_ids: list[int]) -> tuple[bool, str | None]:
    """Whether this exact group of players (already dragged together) is a
    legal team for the category. Returns (ok, complaint-or-None)."""
    rule = GENDER_RULE.get(category)
    if not rule:
        return True, None
    if len(member_ids) != len(rule):
        return False, None
    genders = [get_player(i)["gender"] for i in member_ids]
    if any(g is None for g in genders):
        return False, tr("gender not set")
    ok = sorted(genders) == sorted(rule)
    return ok, (None if ok else tr("needs {g}", g="+".join(rule)))


def add_entry(event_id, player1_id, player2_id=None, seed=None, actor=None) -> int:
    ev = get_event(event_id)
    if not ev:
        raise RuleError(tr("Event not found."))
    size = TEAM_SIZE[ev["category"]]
    if size == 2 and not player2_id:
        raise RuleError(tr("Doubles entries need two players."))
    if size == 1:
        player2_id = None
    if player2_id and player1_id == player2_id:
        raise RuleError(tr("A player cannot partner themselves."))

    for pid in filter(None, (player1_id, player2_id)):
        clash = db.query_one(
            "SELECT id FROM entries WHERE event_id = ? AND (player1_id = ? OR player2_id = ?)",
            (event_id, pid, pid))
        if clash:
            p = get_player(pid)
            raise RuleError(tr("{name} is already entered in {event}.", name=p["name"], event=event_label(ev)))

    p1 = get_player(player1_id)
    p2 = get_player(player2_id) if player2_id else None
    name = entry_display_name(ev, p1, p2)
    eid = db.insert("entries", {
        "event_id": event_id, "name": name, "player1_id": player1_id,
        "player2_id": player2_id, "seed": seed, "status": "active",
        "created_at": db.now(), "created_by": actor,
    })
    db.log(actor, ev["tournament_id"], "entry", eid, "create", name)
    return eid


def list_entries(event_id: int, active_only=True) -> list[dict]:
    sql = "SELECT * FROM entries WHERE event_id = ?"
    if active_only:
        sql += " AND status = 'active'"
    sql += " ORDER BY CASE WHEN seed IS NULL THEN 1 ELSE 0 END, seed, name"
    return db.query(sql, (event_id,))


def get_entry(entry_id: int) -> dict | None:
    return db.query_one("SELECT * FROM entries WHERE id = ?", (entry_id,))


def entry_name(entry_id, cache=None) -> str:
    if entry_id is None:
        return "—"
    if cache and entry_id in cache:
        return cache[entry_id]["name"]
    e = get_entry(entry_id)
    return e["name"] if e else "—"


def set_seed(entry_id, seed, actor=None):
    db.update("entries", entry_id, {"seed": seed})


def set_seed_order(event_id, ordered_entry_ids: list[int], actor=None):
    """Bulk-set seed = position in the given order (1-based). Used by the
    drag-to-reorder seeding list on the Draws page, before a draw exists."""
    for i, eid in enumerate(ordered_entry_ids, start=1):
        db.update("entries", eid, {"seed": i})
    ev_row = get_entry(ordered_entry_ids[0]) if ordered_entry_ids else None
    ev_id = ev_row["event_id"] if ev_row else event_id
    db.log(actor, None, "event", ev_id, "reseed", f"{len(ordered_entry_ids)} entries")


def set_entry_pool(entry_id, pool: str | None, actor=None):
    """Manually place an entry into a pool ahead of the draw being built.
    `build_pools` honors these if every active entry has one set."""
    db.update("entries", entry_id, {"pool": pool})
    db.log(actor, None, "entry", entry_id, "set_pool", pool or "")


def delete_entry(entry_id, actor=None):
    played = db.query_one(
        "SELECT id FROM matches WHERE (entry_a_id = ? OR entry_b_id = ?) AND status IN "
        f"('{STATUS_DONE}', '{STATUS_LIVE}')", (entry_id, entry_id))
    if played:
        raise RuleError(tr("This entry already has a live or completed match. Withdraw them instead."))
    e = get_entry(entry_id)
    db.execute("DELETE FROM matches WHERE (entry_a_id = ? OR entry_b_id = ?) AND status = ?",
               (entry_id, entry_id, STATUS_PENDING))
    db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    if e:
        db.log(actor, None, "entry", entry_id, "delete", e["name"])


def withdraw_entry(entry_id, actor=None):
    """Keep completed results, concede every remaining match."""
    db.update("entries", entry_id, {"status": "withdrawn"})
    pending = db.query(
        "SELECT * FROM matches WHERE (entry_a_id = ? OR entry_b_id = ?) AND status IN "
        f"('{STATUS_PENDING}', '{STATUS_LIVE}')", (entry_id, entry_id))
    for m in pending:
        other = m["entry_b_id"] if m["entry_a_id"] == entry_id else m["entry_a_id"]
        if other:
            _finish_match(m["id"], winner_id=other, loser_id=entry_id,
                          status=STATUS_BYE, actor=actor, note="walkover")
        else:
            _void_match(m["id"])
    db.log(actor, None, "entry", entry_id, "withdraw", "")


def eligible_substitutes(entry_id: int, slot: int) -> list[dict]:
    """Players who could legally fill this slot on this entry right now:
    the right gender for the category, not already entered elsewhere in
    this event, and not already the entry's other half."""
    e = get_entry(entry_id)
    if not e:
        return []
    ev = get_event(e["event_id"])
    roster = list_players(ev["tournament_id"])
    pool = eligible_players(ev["category"], slot, roster)
    taken = {row["player1_id"] for row in list_entries(e["event_id"], active_only=False)
            if row["id"] != entry_id}
    taken |= {row["player2_id"] for row in list_entries(e["event_id"], active_only=False)
             if row["id"] != entry_id and row["player2_id"]}
    other = e["player2_id"] if slot == 0 else e["player1_id"]
    current = e["player1_id"] if slot == 0 else e["player2_id"]
    return [p for p in pool if p["id"] not in taken and p["id"] != other and p["id"] != current]


def substitute_player(entry_id: int, old_player_id: int, new_player_id: int, actor=None):
    """Swap one player out of an entry for another, in place — the entry
    keeps its seed, its pool, and its exact position in any draw that
    already exists. Built for the last-minute withdrawal: the team stays
    right where it is, only who's actually on court changes.
    """
    e = get_entry(entry_id)
    if not e:
        raise RuleError(tr("Entry not found."))
    if e["player1_id"] != old_player_id and e["player2_id"] != old_player_id:
        raise RuleError(tr("That player isn't part of this entry."))
    if old_player_id == new_player_id:
        raise RuleError(tr("Pick a different player to bring in."))

    ev = get_event(e["event_id"])
    new_p = get_player(new_player_id)
    if not new_p:
        raise RuleError(tr("Player not found."))
    slot = 0 if e["player1_id"] == old_player_id else 1
    need = slot_gender(ev["category"], slot)
    if need and new_p.get("gender") != need:
        raise RuleError(tr("{name} isn't eligible for this slot in {event} (needs a man)." if need == "M"
                           else "{name} isn't eligible for this slot in {event} (needs a woman).",
                           name=new_p["name"], event=event_label(ev)))
    other_slot_id = e["player2_id"] if slot == 0 else e["player1_id"]
    if new_player_id == other_slot_id:
        raise RuleError(tr("{name} is already this entry's other half.", name=new_p["name"]))
    clash = db.query_one(
        "SELECT id FROM entries WHERE event_id = ? AND id != ? AND status = 'active' "
        "AND (player1_id = ? OR player2_id = ?)",
        (e["event_id"], entry_id, new_player_id, new_player_id))
    if clash:
        raise RuleError(tr("{name} is already entered elsewhere in {event}.", name=new_p["name"], event=event_label(ev)))

    field = "player1_id" if slot == 0 else "player2_id"
    new_p1_id = new_player_id if slot == 0 else e["player1_id"]
    new_p2_id = new_player_id if slot == 1 else e["player2_id"]
    p1 = get_player(new_p1_id)
    p2 = get_player(new_p2_id) if new_p2_id else None
    new_name = entry_display_name(ev, p1, p2)

    db.update("entries", entry_id, {field: new_player_id, "name": new_name})
    # Any match already wired to this entry just displays whatever the
    # entry's current name is — nothing about the draw itself needs to move.
    old_p = get_player(old_player_id)
    old_name = old_p["name"] if old_p else "?"
    db.log(actor, ev["tournament_id"], "entry", entry_id, "substitute",
          f"{old_name} → {new_p['name']}")
    return new_name


# --------------------------------------------------------------------------
# Matches
# --------------------------------------------------------------------------

def create_match(event_id, stage, round_no, match_no, round_label=None, pool=None,
                 entry_a_id=None, entry_b_id=None, best_of=3) -> int:
    return db.insert("matches", {
        "event_id": event_id, "stage": stage, "pool": pool, "round_no": round_no,
        "round_label": round_label, "match_no": match_no,
        "entry_a_id": entry_a_id, "entry_b_id": entry_b_id,
        "best_of": best_of, "status": STATUS_PENDING, "version": 1,
        "updated_at": db.now(),
    })


def link(match_id, next_match_id=None, next_slot=None,
         loser_next_match_id=None, loser_next_slot=None):
    data = {}
    if next_match_id is not None:
        data["next_match_id"] = next_match_id
        data["next_slot"] = next_slot
    if loser_next_match_id is not None:
        data["loser_next_match_id"] = loser_next_match_id
        data["loser_next_slot"] = loser_next_slot
    db.update("matches", match_id, data)


def list_matches(event_id: int, statuses=None) -> list[dict]:
    sql = "SELECT * FROM matches WHERE event_id = ?"
    params: tuple = (event_id,)
    if statuses:
        marks = ", ".join("?" for _ in statuses)
        sql += f" AND status IN ({marks})"
        params += tuple(statuses)
    sql += " ORDER BY stage, round_no, match_no, id"
    return db.query(sql, params)


def get_match(mid: int) -> dict | None:
    return db.query_one("SELECT * FROM matches WHERE id = ?", (mid,))


def get_games(mid: int) -> list[dict]:
    return db.query("SELECT * FROM games WHERE match_id = ? ORDER BY game_no", (mid,))


def games_for_event(event_id: int) -> dict[int, list[dict]]:
    rows = db.query(
        "SELECT g.* FROM games g JOIN matches m ON m.id = g.match_id "
        "WHERE m.event_id = ? ORDER BY g.match_id, g.game_no", (event_id,))
    out: dict[int, list[dict]] = {}
    for r in rows:
        out.setdefault(r["match_id"], []).append(r)
    return out


def entries_map(event_id: int) -> dict[int, dict]:
    return {e["id"]: e for e in list_entries(event_id, active_only=False)}


# ---- tournament-wide bulk reads --------------------------------------------
#
# Looping "for each event: one query" adds up fast once a database is remote
# (Streamlit Cloud talking to a hosted Postgres, say) — every query in that
# loop is its own network round trip. These do the same job in one query
# each, regardless of how many events the tournament has, for anything that
# needs to look across the whole tournament at once (the Live board, the
# Venue display, and the court scheduler all do).

def list_matches_for_tournament(tournament_id: int) -> list[dict]:
    return db.query(
        "SELECT m.* FROM matches m JOIN events e ON e.id = m.event_id "
        "WHERE e.tournament_id = ? "
        "ORDER BY e.id, m.stage, m.round_no, m.match_no, m.id", (tournament_id,))


def entries_map_for_tournament(tournament_id: int) -> dict[int, dict]:
    rows = db.query(
        "SELECT en.* FROM entries en JOIN events e ON e.id = en.event_id "
        "WHERE e.tournament_id = ?", (tournament_id,))
    return {r["id"]: r for r in rows}


def games_for_tournament(tournament_id: int) -> dict[int, list[dict]]:
    rows = db.query(
        "SELECT g.* FROM games g JOIN matches m ON m.id = g.match_id "
        "JOIN events e ON e.id = m.event_id WHERE e.tournament_id = ? "
        "ORDER BY g.match_id, g.game_no", (tournament_id,))
    out: dict[int, list[dict]] = {}
    for r in rows:
        out.setdefault(r["match_id"], []).append(r)
    return out


def match_ready(m: dict) -> bool:
    return m["entry_a_id"] is not None and m["entry_b_id"] is not None


# ---- score validation ----------------------------------------------------

validate_game = rules.validate_game


def validate_match_scores(games: list[tuple[int, int]], best_of: int, rule: dict) -> str | None:
    if not games:
        return tr("Enter at least one game.")
    need = best_of // 2 + 1
    wa = wb = 0
    for i, (a, b) in enumerate(games, start=1):
        err = validate_game(a, b, rule)
        if err:
            return tr("Game {i}: {err}", i=i, err=err)
        if wa == need or wb == need:
            return tr("Game {i} was not needed — the match was already decided.", i=i)
        if a > b:
            wa += 1
        else:
            wb += 1
    if wa < need and wb < need:
        return tr("Best of {n}: someone needs {need} game(s) to win.", n=best_of, need=need)
    return None


# ---- writing results -----------------------------------------------------

def start_match(match_id, actor=None, court=None, first_serving="a", right=None):
    """Put a match on court. `first_serving` ("a"/"b") is who won the serve,
    and for doubles `right` = {"a": 0|1, "b": 0|1} says which player of each
    side starts in the right (even) court — 0 is the entry's first player."""
    m = get_match(match_id)
    if not m:
        raise RuleError(tr("Match not found."))
    if not match_ready(m):
        raise RuleError(tr("Both sides must be decided before the match can start."))
    if m["status"] == STATUS_DONE:
        raise RuleError(tr("This match is already finished."))
    ev = get_event(m["event_id"])
    state = rules.new_game(doubles=is_doubles(m), system=scoring_system(ev),
                           first_serving=first_serving if first_serving in ("a", "b") else "a",
                           right=right)
    db.update("matches", match_id, {
        "status": STATUS_LIVE, "started_at": m["started_at"] or db.now(),
        "court": court if court is not None else m["court"],
        "cur_a": 0, "cur_b": 0, "serve_state": json.dumps(state),
        "version": m["version"] + 1, "updated_at": db.now(), "updated_by": actor,
    })
    db.log(actor, None, "match", match_id, "start", court or "")


CLAIM_MINUTES = 5


def claim_holder(m: dict) -> str | None:
    """Who is currently typing into this match, if the claim is still fresh."""
    if not m.get("locked_by") or not m.get("locked_at"):
        return None
    from datetime import datetime, timedelta, timezone
    try:
        when = datetime.fromisoformat(m["locked_at"])
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - when > timedelta(minutes=CLAIM_MINUTES):
        return None
    return m["locked_by"]


def claim_match(match_id, actor):
    """Soft lock. Advisory only — it warns, it never blocks a correction.

    Skips the write entirely once the actor already holds a fresh-enough
    claim, instead of touching the database on every single render. This
    function runs on every point tap and every auto-refresh of a live
    match — on a remote database, a wasted round trip here is exactly the
    kind of thing that makes every button feel slow.
    """
    from datetime import datetime, timedelta, timezone
    m = get_match(match_id)
    if not m:
        return
    holder = claim_holder(m)
    if holder and holder != actor:
        return holder
    if holder == actor:
        try:
            when = datetime.fromisoformat(m["locked_at"])
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - when < timedelta(minutes=CLAIM_MINUTES / 2):
                return None   # still comfortably fresh — nothing to write
        except (TypeError, ValueError):
            pass
    db.update("matches", match_id, {"locked_by": actor, "locked_at": db.now()})
    return None


def release_match(match_id, actor=None):
    db.update("matches", match_id, {"locked_by": None, "locked_at": None})


def recent_activity(tournament_id: int, limit: int = 12) -> list[dict]:
    return db.query(
        "SELECT * FROM audit_log WHERE tournament_id = ? OR tournament_id IS NULL "
        "ORDER BY id DESC LIMIT ?", (tournament_id, limit))


def set_court(match_id, court, actor=None):
    db.update("matches", match_id, {"court": court, "updated_at": db.now(), "updated_by": actor})
    db.log(actor, None, "match", match_id, "set_court", court or "")


# ---- live, point-by-point scoring -----------------------------------------
#
# `games` holds only *confirmed* completed games. `matches.cur_a`/`cur_b` is
# the running tally for whichever game is currently in progress — every tap
# of +1/-1 writes straight to the database, so it's visible on the Live board
# (and to every other admin or referee looking at the same match) within one
# poll, and it's exactly what makes each adjustment auditable: the log below
# records every single point, not just the final score.

def adjust_point(match_id, side: str, delta: int, actor=None):
    m = get_match(match_id)
    if not m:
        raise RuleError(tr("Match not found."))
    if m["status"] != STATUS_LIVE:
        raise RuleError(tr("Start the match before adjusting points."))
    if side not in ("a", "b"):
        raise RuleError(tr("side must be 'a' or 'b'."))
    col = "cur_a" if side == "a" else "cur_b"
    new_val = max(0, int(m[col]) + delta)
    a_val = new_val if side == "a" else m["cur_a"]
    b_val = new_val if side == "b" else m["cur_b"]
    data = {col: new_val, "updated_at": db.now(), "updated_by": actor}
    state = serve_state(m)
    if state:
        # A manual correction bypasses the rally rules, but whether the game
        # is now over still has to follow the score.
        data["serve_state"] = json.dumps(
            rules.recheck_game_over(state, (a_val, b_val), scoring_rule(get_event(m["event_id"]))))
    db.update("matches", match_id, data)
    db.log(actor, None, "match", match_id, "point", f"{a_val}-{b_val} (manual correction)")
    return a_val, b_val


# ---- rally-by-rally refereeing ---------------------------------------------
#
# The referee only ever answers "who won the rally?" — `tourney.rules` decides
# whether that's a point, a second server or a side out, who serves next and
# from which court. Every rally (and timeout, and serve setup) is logged with
# the state before and after it, so Undo is exact.

def is_doubles(m: dict) -> bool:
    a = get_entry(m["entry_a_id"]) if m.get("entry_a_id") else None
    if not a:
        return False
    ev = get_event(a["event_id"])
    if ev and ev["category"] != "QM":
        return TEAM_SIZE[ev["category"]] == 2
    return " / " in a["name"]


def side_players(m: dict) -> dict:
    """{"a": [{"id": pid|None, "name": str}, ...], "b": [...]} for the court
    diagram and name editing. Quick-match entries have no registered players,
    so their names come from the entry name ("A" or "A / B")."""
    out = {}
    for side, eid in (("a", m.get("entry_a_id")), ("b", m.get("entry_b_id"))):
        e = get_entry(eid) if eid else None
        if not e:
            out[side] = []
            continue
        ids = [pid for pid in (e["player1_id"], e["player2_id"]) if pid]
        if ids:
            out[side] = [{"id": pid, "name": (get_player(pid) or {}).get("name", "?")} for pid in ids]
        else:
            out[side] = [{"id": None, "name": n} for n in e["name"].split(" / ")]
    return out


def serve_state(m: dict) -> dict | None:
    raw = m.get("serve_state")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def ensure_serve_state(m: dict) -> dict:
    """Matches started before rally refereeing existed have no serve state;
    give them a default one (side A serving, first players on the right)."""
    state = serve_state(m)
    if state:
        return state
    ev = get_event(m["event_id"])
    state = rules.new_game(doubles=is_doubles(m), system=scoring_system(ev))
    state = rules.recheck_game_over(state, (m["cur_a"], m["cur_b"]), scoring_rule(ev))
    db.update("matches", m["id"], {"serve_state": json.dumps(state)})
    return state


def games_won(match_id) -> dict:
    gs = get_games(match_id)
    wa = sum(1 for g in gs if g["score_a"] > g["score_b"])
    return {"a": wa, "b": len(gs) - wa}


def current_game_no(match_id) -> int:
    return len(get_games(match_id)) + 1


def _live_match(match_id) -> dict:
    m = get_match(match_id)
    if not m:
        raise RuleError(tr("Match not found."))
    if m["status"] != STATUS_LIVE:
        raise RuleError(tr("Start the match first."))
    return m


def _log_rally(m, kind, winner, before_state, after_state, before_score, after_score, actor):
    game_no = current_game_no(m["id"])
    seq = (db.query_one("SELECT MAX(seq) AS s FROM rallies WHERE match_id = ? AND game_no = ?",
                        (m["id"], game_no)) or {}).get("s") or 0
    db.insert("rallies", {
        "match_id": m["id"], "game_no": game_no, "seq": seq + 1, "kind": kind, "winner": winner,
        "a_before": before_score[0], "b_before": before_score[1],
        "a_after": after_score[0], "b_after": after_score[1],
        "state_before": json.dumps(before_state), "state_after": json.dumps(after_state),
        "created_at": db.now(), "actor": actor,
    })


def _save_live(m, state, score, actor, bump_version=False):
    data = {"cur_a": score[0], "cur_b": score[1], "serve_state": json.dumps(state),
            "updated_at": db.now(), "updated_by": actor}
    if bump_version:
        data["version"] = m["version"] + 1
    db.update("matches", m["id"], data)


def record_rally(match_id, winner: str, actor=None) -> list[str]:
    """The referee's one button: side `winner` won the rally. Returns the
    rule events ("point", "side_out", "second_server", "switch_ends",
    "game_over") so the view can say what just happened."""
    m = _live_match(match_id)
    ev = get_event(m["event_id"])
    rule = scoring_rule(ev)
    state = ensure_serve_state(m)
    before = (m["cur_a"], m["cur_b"])
    deciding = rules.is_deciding_game(games_won(match_id), m["best_of"])
    try:
        new_state, score, events = rules.apply_rally(state, before, winner, rule, deciding)
    except ValueError as e:
        raise RuleError(str(e))
    _save_live(m, new_state, score, actor)
    _log_rally(m, "rally", winner, state, new_state, before, score, actor)
    db.log(actor, None, "match", match_id, "rally",
           f"{winner.upper()} won rally → {rules.score_call(new_state, score)} "
           f"({', '.join(events)})")
    return events


def undo_rally(match_id, actor=None) -> str:
    """Step back exactly one logged action (rally, timeout or setup change)
    in the current game. Returns what was undone."""
    m = _live_match(match_id)
    game_no = current_game_no(match_id)
    last = db.query_one("SELECT * FROM rallies WHERE match_id = ? AND game_no = ? "
                        "ORDER BY seq DESC LIMIT 1", (match_id, game_no))
    if not last:
        raise RuleError(tr("Nothing to undo in this game yet."))
    db.execute("DELETE FROM rallies WHERE id = ?", (last["id"],))
    db.update("matches", match_id, {
        "cur_a": last["a_before"], "cur_b": last["b_before"],
        "serve_state": last["state_before"], "updated_at": db.now(), "updated_by": actor})
    db.log(actor, None, "match", match_id, "undo", f"{last['kind']} {last['winner'] or ''}")
    return last["kind"]


def call_timeout(match_id, side: str, actor=None):
    m = _live_match(match_id)
    rule = scoring_rule(get_event(m["event_id"]))
    state = ensure_serve_state(m)
    try:
        new_state = rules.use_timeout(state, side, rule)
    except ValueError as e:
        raise RuleError(str(e))
    score = (m["cur_a"], m["cur_b"])
    _save_live(m, new_state, score, actor)
    _log_rally(m, "timeout", side, state, new_state, score, score, actor)
    db.log(actor, None, "match", match_id, "timeout", side.upper())


def switch_ends(match_id, actor=None):
    """Flip which side the teams are shown on (the referee's view of the court)."""
    m = _live_match(match_id)
    state = ensure_serve_state(m)
    new_state = rules.toggle_ends(state)
    score = (m["cur_a"], m["cur_b"])
    _save_live(m, new_state, score, actor)
    _log_rally(m, "switch_ends", None, state, new_state, score, score, actor)


def setup_serve(match_id, first_serving: str, right: dict | None = None, actor=None):
    """Change who serves first / who starts in the right court. Only before
    the first rally of a game — after that the rules decide."""
    m = _live_match(match_id)
    state = ensure_serve_state(m)
    if state.get("rallies") or m["cur_a"] or m["cur_b"]:
        raise RuleError(tr("Serve order can only be changed before the first rally of a game. "
                           "Undo back to 0-0 first."))
    new_state = rules.reconfigure(state, first_serving=first_serving, right=right)
    score = (m["cur_a"], m["cur_b"])
    _save_live(m, new_state, score, actor)
    _log_rally(m, "setup", first_serving, state, new_state, score, score, actor)


def confirm_current_game(match_id, actor=None) -> bool:
    """Locks the live game in once it has reached a valid final score, and
    finishes the match outright if that was the deciding game. Returns True
    if the match is now finished, False if there's another game to play."""
    m = get_match(match_id)
    if not m:
        raise RuleError(tr("Match not found."))
    if m["status"] != STATUS_LIVE:
        raise RuleError(tr("This match isn't live."))
    ev = get_event(m["event_id"])
    rule = scoring_rule(ev)
    a, b = int(m["cur_a"]), int(m["cur_b"])
    err = validate_game(a, b, rule)
    if err:
        raise RuleError(err)

    game_no = len(get_games(match_id)) + 1
    db.insert("games", {"match_id": match_id, "game_no": game_no, "score_a": a, "score_b": b})
    state = serve_state(m)
    if state:
        # Remember how the game ended (so "undo last game" can restore it),
        # then set up the next one: change ends, other side serves first.
        db.insert("rallies", {
            "match_id": match_id, "game_no": game_no, "seq": 10 ** 6, "kind": "game_end",
            "winner": "a" if a > b else "b", "a_before": a, "b_before": b, "a_after": a,
            "b_after": b, "state_before": json.dumps(state), "state_after": json.dumps(state),
            "created_at": db.now(), "actor": actor})
    db.update("matches", match_id, {
        "cur_a": 0, "cur_b": 0, "version": m["version"] + 1,
        "serve_state": json.dumps(rules.next_game(state)) if state else None,
        "updated_at": db.now(), "updated_by": actor,
    })
    db.log(actor, None, "match", match_id, "game", f"Game {game_no}: {a}-{b}")

    games = [(g["score_a"], g["score_b"]) for g in get_games(match_id)]
    need = m["best_of"] // 2 + 1
    wa = sum(1 for x, y in games if x > y)
    wb = len(games) - wa
    if wa >= need or wb >= need:
        winner = m["entry_a_id"] if wa > wb else m["entry_b_id"]
        loser = m["entry_b_id"] if wa > wb else m["entry_a_id"]
        _finish_match(match_id, winner, loser, STATUS_DONE, actor,
                      note=" ".join(f"{x}-{y}" for x, y in games))
        return True
    return False


def undo_last_game(match_id, actor=None):
    """Pulls the most recently confirmed game back into 'in progress' — for
    when the desk taps confirm by mistake."""
    m = get_match(match_id)
    if not m:
        raise RuleError(tr("Match not found."))
    games = get_games(match_id)
    if not games:
        raise RuleError(tr("No confirmed games to undo yet."))
    last = max(games, key=lambda g: g["game_no"])
    end = db.query_one("SELECT * FROM rallies WHERE match_id = ? AND game_no = ? AND kind = 'game_end'",
                       (match_id, last["game_no"]))
    db.execute("DELETE FROM games WHERE id = ?", (last["id"],))
    # Rallies already played in the game that had started since are discarded.
    db.execute("DELETE FROM rallies WHERE match_id = ? AND (game_no > ? OR kind = 'game_end')",
               (match_id, last["game_no"]))
    data = {"cur_a": last["score_a"], "cur_b": last["score_b"],
            "updated_at": db.now(), "updated_by": actor}
    if end:
        data["serve_state"] = end["state_before"]
    elif m.get("serve_state"):
        ev = get_event(m["event_id"])
        data["serve_state"] = json.dumps(rules.recheck_game_over(
            serve_state(m), (last["score_a"], last["score_b"]), scoring_rule(ev)))
    db.update("matches", match_id, data)
    db.log(actor, None, "match", match_id, "undo_game", f"{last['score_a']}-{last['score_b']}")


def submit_score(match_id, games: list[tuple[int, int]], actor=None, expected_version=None,
                 retire_side=None):
    """Record a final score.

    `expected_version` implements optimistic locking: if a second admin saved
    this match while you had the form open, the save is rejected instead of
    silently overwriting them.
    """
    m = get_match(match_id)
    if not m:
        raise RuleError(tr("Match not found."))
    if expected_version is not None and int(expected_version) != int(m["version"]):
        raise ConflictError(tr(
            "{who} saved this match a moment ago. Reload to see the current score before "
            "saving again.", who=m["updated_by"] or tr("Another admin")))
    if not match_ready(m):
        raise RuleError(tr("Both sides must be decided before a score can be saved."))

    ev = get_event(m["event_id"])
    rule = scoring_rule(ev)

    if retire_side in ("A", "B"):
        winner = m["entry_b_id"] if retire_side == "A" else m["entry_a_id"]
        loser = m["entry_a_id"] if retire_side == "A" else m["entry_b_id"]
        _write_games(match_id, games)
        _finish_match(match_id, winner, loser, STATUS_DONE, actor, note="retired")
        return

    err = validate_match_scores(games, m["best_of"], rule)
    if err:
        raise RuleError(err)

    wa = sum(1 for a, b in games if a > b)
    wb = len(games) - wa
    winner = m["entry_a_id"] if wa > wb else m["entry_b_id"]
    loser = m["entry_b_id"] if wa > wb else m["entry_a_id"]
    _write_games(match_id, games)
    _finish_match(match_id, winner, loser, STATUS_DONE, actor,
                  note=" ".join(f"{a}-{b}" for a, b in games))


def _write_games(match_id, games):
    db.execute("DELETE FROM games WHERE match_id = ?", (match_id,))
    db.execute("DELETE FROM rallies WHERE match_id = ?", (match_id,))
    for i, (a, b) in enumerate(games, start=1):
        db.insert("games", {"match_id": match_id, "game_no": i, "score_a": a, "score_b": b})


def _finish_match(match_id, winner_id, loser_id, status, actor=None, note=""):
    m = get_match(match_id)
    db.update("matches", match_id, {
        "status": status, "winner_entry_id": winner_id, "loser_entry_id": loser_id,
        "finished_at": db.now(), "version": m["version"] + 1,
        "updated_at": db.now(), "updated_by": actor,
    })
    db.log(actor, None, "match", match_id, "result", note)
    propagate(match_id)
    _refresh_event_status(m["event_id"])


def reopen_match(match_id, actor=None):
    """Undo a result. Only allowed if nothing downstream has been played."""
    m = get_match(match_id)
    if not m:
        raise RuleError(tr("Match not found."))
    for nxt_id, slot in ((m["next_match_id"], m["next_slot"]),
                         (m["loser_next_match_id"], m["loser_next_slot"])):
        if not nxt_id:
            continue
        nxt = get_match(nxt_id)
        if nxt and nxt["status"] in (STATUS_DONE, STATUS_LIVE):
            raise RuleError(tr("{m} has already started. Reopen that one first.",
                               m=i18n.round_label(nxt["round_label"]) or tr("The next match")))
    # Pull the entry back out of the downstream slots.
    for nxt_id, slot, who in ((m["next_match_id"], m["next_slot"], m["winner_entry_id"]),
                              (m["loser_next_match_id"], m["loser_next_slot"], m["loser_entry_id"])):
        if nxt_id and slot:
            col = "entry_a_id" if slot == "A" else "entry_b_id"
            void_col = "a_void" if slot == "A" else "b_void"
            db.execute(f"UPDATE matches SET {col} = NULL, {void_col} = 0 WHERE id = ?", (nxt_id,))
    db.execute("DELETE FROM games WHERE match_id = ?", (match_id,))
    db.execute("DELETE FROM rallies WHERE match_id = ?", (match_id,))
    db.update("matches", match_id, {
        "status": STATUS_PENDING, "winner_entry_id": None, "loser_entry_id": None,
        "finished_at": None, "serve_state": None, "cur_a": 0, "cur_b": 0, "version": m["version"] + 1,
        "updated_at": db.now(), "updated_by": actor,
    })
    db.log(actor, None, "match", match_id, "reopen", "")
    _refresh_event_status(m["event_id"])


def _void_match(match_id):
    m = get_match(match_id)
    if not m or m["status"] in (STATUS_DONE, STATUS_BYE):
        return
    db.update("matches", match_id, {"status": STATUS_VOID, "updated_at": db.now()})
    _push(m["next_match_id"], m["next_slot"], None, void=True)
    _push(m["loser_next_match_id"], m["loser_next_slot"], None, void=True)


def _push(target_match_id, slot, entry_id, void=False):
    if not target_match_id or not slot:
        return
    col = "entry_a_id" if slot == "A" else "entry_b_id"
    void_col = "a_void" if slot == "A" else "b_void"
    if void:
        db.execute(f"UPDATE matches SET {void_col} = 1 WHERE id = ?", (target_match_id,))
    else:
        db.execute(f"UPDATE matches SET {col} = ?, {void_col} = 0 WHERE id = ?",
                   (entry_id, target_match_id))


def propagate(match_id):
    """Send winner/loser onward, then settle any byes this created."""
    m = get_match(match_id)
    if not m:
        return
    if m["status"] in (STATUS_DONE, STATUS_BYE):
        _push(m["next_match_id"], m["next_slot"], m["winner_entry_id"])
        if m["loser_next_match_id"]:
            if m["status"] == STATUS_BYE and m["loser_entry_id"] is None:
                _push(m["loser_next_match_id"], m["loser_next_slot"], None, void=True)
            else:
                _push(m["loser_next_match_id"], m["loser_next_slot"], m["loser_entry_id"])
    resolve_byes(m["event_id"])


def resolve_byes(event_id: int):
    """Repeatedly walk the draw completing walkovers until it settles."""
    for _ in range(64):
        changed = False
        for m in list_matches(event_id, statuses=[STATUS_PENDING]):
            a, b = m["entry_a_id"], m["entry_b_id"]
            a_void, b_void = bool(m["a_void"]), bool(m["b_void"])
            if a_void and b_void:
                _void_match(m["id"])
                changed = True
            elif a is not None and b_void:
                db.update("matches", m["id"], {
                    "status": STATUS_BYE, "winner_entry_id": a, "loser_entry_id": None,
                    "finished_at": db.now(), "updated_at": db.now()})
                _push(m["next_match_id"], m["next_slot"], a)
                if m["loser_next_match_id"]:
                    _push(m["loser_next_match_id"], m["loser_next_slot"], None, void=True)
                changed = True
            elif b is not None and a_void:
                db.update("matches", m["id"], {
                    "status": STATUS_BYE, "winner_entry_id": b, "loser_entry_id": None,
                    "finished_at": db.now(), "updated_at": db.now()})
                _push(m["next_match_id"], m["next_slot"], b)
                if m["loser_next_match_id"]:
                    _push(m["loser_next_match_id"], m["loser_next_slot"], None, void=True)
                changed = True
        if not changed:
            break
    _maybe_bracket_reset(event_id)
    _refresh_event_status(event_id)


def _maybe_bracket_reset(event_id):
    """Double elimination: if the losers-bracket entry wins the grand final,
    create the deciding match (the 'bracket reset')."""
    ev = get_event(event_id)
    if not ev or ev["format"] != "double_elim" or not ev["gf_reset"]:
        return
    gfs = [m for m in list_matches(event_id) if m["stage"] == STAGE_GF]
    if len(gfs) != 1:
        return
    gf = gfs[0]
    if gf["status"] != STATUS_DONE or not gf["winner_entry_id"]:
        return
    # Slot B holds the losers-bracket survivor. If they won, both sides have one loss.
    if gf["winner_entry_id"] != gf["entry_b_id"]:
        return
    mid = create_match(event_id, STAGE_GF, gf["round_no"] + 1, 1,
                       round_label="Grand Final (reset)",
                       entry_a_id=gf["entry_a_id"], entry_b_id=gf["entry_b_id"],
                       best_of=gf["best_of"])
    db.log(None, None, "match", mid, "create", "grand final reset")


def _refresh_event_status(event_id):
    ev = get_event(event_id)
    if not ev:
        return
    rows = list_matches(event_id)
    if not rows:
        status = "setup"
    elif any(m["status"] in OPEN_STATUSES for m in rows):
        status = "running"
    else:
        status = "complete"
    if status != ev["status"]:
        db.update("events", event_id, {"status": status})


# --------------------------------------------------------------------------
# Fixture editing helpers
# --------------------------------------------------------------------------

def have_met(event_id, entry_a, entry_b, exclude_match=None) -> list[dict]:
    """Every prior or scheduled meeting between two entries in this event."""
    if not entry_a or not entry_b:
        return []
    sql = ("SELECT * FROM matches WHERE event_id = ? AND status != ? AND "
           "((entry_a_id = ? AND entry_b_id = ?) OR (entry_a_id = ? AND entry_b_id = ?))")
    params = (event_id, STATUS_VOID, entry_a, entry_b, entry_b, entry_a)
    rows = db.query(sql, params)
    if exclude_match:
        rows = [r for r in rows if r["id"] != exclude_match]
    return rows


def set_match_entry(match_id, slot, entry_id, actor=None, allow_rematch=False):
    """Manually place an entry into a fixture, with rematch protection."""
    m = get_match(match_id)
    if not m:
        raise RuleError(tr("Match not found."))
    if m["status"] in (STATUS_DONE, STATUS_BYE):
        raise RuleError(tr("Finished matches cannot be re-drawn. Reopen the match first."))
    other = m["entry_b_id"] if slot == "A" else m["entry_a_id"]
    if entry_id and other and entry_id == other:
        raise RuleError(tr("An entry cannot play itself."))
    if entry_id and other and not allow_rematch:
        prior = have_met(m["event_id"], entry_id, other, exclude_match=match_id)
        if prior:
            names = ", ".join(i18n.round_label(p["round_label"]) or tr("Match {n}", n=p["match_no"]) for p in prior)
            raise RuleError(tr(
                "{a} and {b} already meet in: {where}. Tick 'allow rematch' if that is intended.",
                a=entry_name(entry_id), b=entry_name(other), where=names))
    col = "entry_a_id" if slot == "A" else "entry_b_id"
    void_col = "a_void" if slot == "A" else "b_void"
    db.execute(f"UPDATE matches SET {col} = ?, {void_col} = 0, version = version + 1, "
               "updated_at = ?, updated_by = ? WHERE id = ?",
               (entry_id, db.now(), actor, match_id))
    db.log(actor, None, "match", match_id, "set_entry", f"{slot}={entry_id}")


def swap_entries(match_a_id, slot_a, match_b_id, slot_b, actor=None, allow_rematch=False):
    """Exchange two players between fixtures, checking both resulting pairings."""
    ma, mb = get_match(match_a_id), get_match(match_b_id)
    if not ma or not mb:
        raise RuleError(tr("Match not found."))
    for m in (ma, mb):
        if m["status"] in (STATUS_DONE, STATUS_BYE, STATUS_LIVE):
            raise RuleError(tr("One of these matches is live or finished."))
    col_a = "entry_a_id" if slot_a == "A" else "entry_b_id"
    col_b = "entry_a_id" if slot_b == "A" else "entry_b_id"
    val_a, val_b = ma[col_a], mb[col_b]
    opp_a = ma["entry_b_id"] if slot_a == "A" else ma["entry_a_id"]
    opp_b = mb["entry_b_id"] if slot_b == "A" else mb["entry_a_id"]

    problems = []
    if not allow_rematch:
        if val_b and opp_a and have_met(ma["event_id"], val_b, opp_a, exclude_match=match_a_id):
            problems.append(f"{entry_name(val_b)} vs {entry_name(opp_a)}")
        if val_a and opp_b and have_met(mb["event_id"], val_a, opp_b, exclude_match=match_b_id):
            problems.append(f"{entry_name(val_a)} vs {entry_name(opp_b)}")
    if val_b and val_b == opp_a:
        problems.append(tr("an entry would face itself"))
    if val_a and val_a == opp_b:
        problems.append(tr("an entry would face itself"))
    if problems:
        raise RuleError(tr("That swap creates a repeat matchup: {x}", x="; ".join(problems)))

    db.execute(f"UPDATE matches SET {col_a} = ?, version = version + 1, updated_at = ?, "
               "updated_by = ? WHERE id = ?", (val_b, db.now(), actor, match_a_id))
    db.execute(f"UPDATE matches SET {col_b} = ?, version = version + 1, updated_at = ?, "
               "updated_by = ? WHERE id = ?", (val_a, db.now(), actor, match_b_id))
    db.log(actor, None, "match", match_a_id, "swap", f"with {match_b_id}")


def rematch_audit(event_id: int) -> list[dict]:
    """Every pair scheduled to meet more than once, so you can spot a bad draw."""
    rows = db.query(
        "SELECT * FROM matches WHERE event_id = ? AND status != ? AND "
        "entry_a_id IS NOT NULL AND entry_b_id IS NOT NULL", (event_id, STATUS_VOID))
    seen: dict[tuple, list] = {}
    for m in rows:
        key = tuple(sorted((m["entry_a_id"], m["entry_b_id"])))
        seen.setdefault(key, []).append(m)
    out = []
    for key, ms in seen.items():
        if len(ms) > 1:
            out.append({"entries": key, "matches": ms})
    return out
