"""Court assignment across every event in a tournament.

The problem this solves: a player entered in Men's Singles and Mixed Doubles is
one human being. The draw engine has no idea those two entries share a person,
so without this module the desk will happily call them to Court 1 and Court 4 at
the same time. Every function here works at the *player* level across all five
categories, not at the entry level within one event.
"""

from __future__ import annotations

from . import db, i18n, models
from .i18n import tr
from .constants import CATEGORIES, STATUS_LIVE, STATUS_PENDING


def entry_players(entry: dict) -> set[int]:
    if not entry:
        return set()
    return {p for p in (entry.get("player1_id"), entry.get("player2_id")) if p}


def tournament_context(tournament_id: int) -> dict:
    """Everything the scheduler needs, read once — as a handful of bulk
    queries rather than one per event, since every query here is a network
    round trip on a remote database."""
    events = {e["id"]: e for e in models.list_events(tournament_id)}
    entries = models.entries_map_for_tournament(tournament_id)
    matches = models.list_matches_for_tournament(tournament_id)
    players = {p["id"]: p for p in models.list_players(tournament_id)}
    return {"events": events, "entries": entries, "matches": matches, "players": players}


def match_players(m: dict, ctx: dict) -> set[int]:
    out = set()
    for side in (m["entry_a_id"], m["entry_b_id"]):
        out |= entry_players(ctx["entries"].get(side))
    return out


def busy_players(ctx: dict) -> dict[int, dict]:
    """Player id → the live match they are currently playing."""
    busy: dict[int, dict] = {}
    for m in ctx["matches"]:
        if m["status"] != STATUS_LIVE:
            continue
        for pid in match_players(m, ctx):
            busy[pid] = m
    return busy


def conflicts(m: dict, ctx: dict, busy: dict[int, dict] | None = None) -> list[str]:
    """Human-readable reasons this match cannot be called right now."""
    busy = busy if busy is not None else busy_players(ctx)
    out = []
    for pid in sorted(match_players(m, ctx)):
        other = busy.get(pid)
        if other and other["id"] != m["id"]:
            pname = ctx["players"].get(pid, {}).get("name", f"player {pid}")
            oev = ctx["events"].get(other["event_id"], {})
            cat = i18n.cat(oev["category"]) if oev.get("category") else tr("another event")
            where = tr(" on {court}", court=other["court"]) if other.get("court") else ""
            out.append(tr("{p} is playing {event}{where}", p=pname, event=cat, where=where))
    return out


def ready_queue(ctx: dict) -> list[dict]:
    """Every match that could be called, in the order it should be called."""
    rows = []
    for m in ctx["matches"]:
        if m["status"] != STATUS_PENDING or not models.match_ready(m):
            continue
        ev = ctx["events"].get(m["event_id"], {})
        rows.append({**m, "_event": ev})
    rows.sort(key=lambda m: (m["round_no"], m["_event"].get("id", 0), m["match_no"]))
    return rows


def callable_queue(ctx: dict) -> list[dict]:
    """The ready queue minus anything whose players are already on court.

    This is what a spectator should see under 'next up' — listing a match whose
    four players are visibly mid-game on other courts just confuses people.
    """
    busy = busy_players(ctx)
    return [m for m in ready_queue(ctx) if not conflicts(m, ctx, busy)]


def occupied_courts(ctx: dict) -> dict[str, dict]:
    """Court name → the live match on it."""
    return {m["court"]: m for m in ctx["matches"]
            if m["status"] == STATUS_LIVE and m.get("court")}


def free_courts(tournament_id: int, ctx: dict) -> list[str]:
    taken = occupied_courts(ctx)
    return [c["name"] for c in models.list_courts(tournament_id)
            if c["status"] == "open" and c["name"] not in taken]


def plan_next(tournament_id: int, ctx: dict | None = None) -> dict:
    """Work out which matches to call onto which courts, without writing anything.

    Greedy down the queue: take the next match whose players are all free, put it
    on the next open court, then treat those players as busy for the rest of the
    pass so the same person is never assigned twice in one round of calls.
    """
    ctx = ctx or tournament_context(tournament_id)
    busy = busy_players(ctx)
    courts = free_courts(tournament_id, ctx)
    queue = ready_queue(ctx)

    assignments, blocked = [], []
    for m in queue:
        reasons = conflicts(m, ctx, busy)
        if reasons:
            blocked.append({"match": m, "reasons": reasons})
            continue
        if not courts:
            blocked.append({"match": m, "reasons": [tr("no court free")]})
            continue
        court = courts.pop(0)
        assignments.append({"match": m, "court": court})
        for pid in match_players(m, ctx):
            busy[pid] = m
    return {"assignments": assignments, "blocked": blocked, "courts_left": courts}


def call_matches(tournament_id: int, assignments: list[dict], actor=None) -> int:
    """Commit a plan: assign the court and put each match on."""
    n = 0
    for a in assignments:
        try:
            models.start_match(a["match"]["id"], actor=actor, court=a["court"])
            n += 1
        except models.RuleError:
            continue
    db.log(actor, tournament_id, "schedule", None, "call", f"{n} match(es) called")
    return n


def player_schedule(tournament_id: int, ctx: dict | None = None) -> list[dict]:
    """Per-player load: how many matches each person still has waiting, and
    whether they are on court right now. This is what stops you scheduling
    someone into three back-to-back matches across three categories."""
    ctx = ctx or tournament_context(tournament_id)
    busy = busy_players(ctx)
    rows = {}
    for pid, p in ctx["players"].items():
        rows[pid] = {"player": p["name"], "club": p.get("club") or "",
                     "events": set(), "remaining": 0, "on_court": None}
    for m in ctx["matches"]:
        if m["status"] not in (STATUS_PENDING, STATUS_LIVE):
            continue
        ev = ctx["events"].get(m["event_id"], {})
        for pid in match_players(m, ctx):
            if pid not in rows:
                continue
            rows[pid]["events"].add(i18n.cat(ev["category"]) if ev.get("category") else "?")
            if m["status"] == STATUS_PENDING:
                rows[pid]["remaining"] += 1
    for pid, m in busy.items():
        if pid in rows:
            rows[pid]["on_court"] = m.get("court") or tr("on court")
    out = [{**r, "events": ", ".join(sorted(r["events"]))} for r in rows.values()
           if r["remaining"] or r["on_court"]]
    out.sort(key=lambda r: (-r["remaining"], r["player"].lower()))
    return out
