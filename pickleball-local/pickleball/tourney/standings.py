"""Ranking.

Tiebreakers run in this order, which matches how most pickleball desks settle
a table:

1. Match win percentage
2. Head-to-head among only the tied entries (a mini-league)
3. Game differential
4. Point differential
5. Points scored
6. Buchholz — strength of the opponents you actually played (Swiss only)
7. Name, so the order is at least stable
"""

from __future__ import annotations

from collections import defaultdict

from . import models
from .constants import (
    STAGE_GF, STAGE_LB, STAGE_PLAYOFF, STAGE_POOL, STAGE_WB,
    STATUS_BYE, STATUS_DONE,
)

COUNTED = (STATUS_DONE, STATUS_BYE)


def _blank(entry) -> dict:
    return {
        "entry": entry, "entry_id": entry["id"], "name": entry["name"],
        "seed": entry.get("seed"), "pool": entry.get("pool"),
        "played": 0, "wins": 0, "losses": 0, "byes": 0,
        "games_won": 0, "games_lost": 0,
        "points_for": 0, "points_against": 0,
        "opponents": [], "status": entry.get("status", "active"),
    }


def _collect(event_id, matches, games_by_match, entries):
    rows = {e["id"]: _blank(e) for e in entries}
    for m in matches:
        if m["status"] not in COUNTED:
            continue
        a, b = m["entry_a_id"], m["entry_b_id"]
        if m["status"] == STATUS_BYE:
            w = m["winner_entry_id"]
            if w in rows:
                rows[w]["wins"] += 1
                rows[w]["byes"] += 1
                rows[w]["played"] += 1
            continue
        if a not in rows or b not in rows:
            continue
        ga = gb = pa = pb = 0
        for g in games_by_match.get(m["id"], []):
            pa += g["score_a"]
            pb += g["score_b"]
            if g["score_a"] > g["score_b"]:
                ga += 1
            elif g["score_b"] > g["score_a"]:
                gb += 1
        for side, opp, gw, gl, pf, pa_ in ((a, b, ga, gb, pa, pb), (b, a, gb, ga, pb, pa)):
            r = rows[side]
            r["played"] += 1
            r["games_won"] += gw
            r["games_lost"] += gl
            r["points_for"] += pf
            r["points_against"] += pa_
            r["opponents"].append(opp)
        if m["winner_entry_id"] in rows:
            rows[m["winner_entry_id"]]["wins"] += 1
        if m["loser_entry_id"] in rows:
            rows[m["loser_entry_id"]]["losses"] += 1
    return rows


def _finalise(rows: dict) -> list[dict]:
    for r in rows.values():
        r["game_diff"] = r["games_won"] - r["games_lost"]
        r["point_diff"] = r["points_for"] - r["points_against"]
        r["win_pct"] = (r["wins"] / r["played"]) if r["played"] else 0.0
        total_pts = r["points_for"] + r["points_against"]
        r["point_pct"] = (r["points_for"] / total_pts) if total_pts else 0.0
    # Buchholz: total wins of everyone you faced.
    for r in rows.values():
        r["buchholz"] = sum(rows[o]["wins"] for o in r["opponents"] if o in rows)
    return list(rows.values())


def _h2h_score(row, group_ids, matches) -> tuple[float, int]:
    """Record against the other tied entries only."""
    wins = played = diff = 0
    me = row["entry_id"]
    for m in matches:
        if m["status"] != STATUS_DONE:
            continue
        a, b = m["entry_a_id"], m["entry_b_id"]
        if me not in (a, b):
            continue
        opp = b if a == me else a
        if opp not in group_ids:
            continue
        played += 1
        if m["winner_entry_id"] == me:
            wins += 1
    return ((wins / played) if played else 0.0), diff


def _sort_table(rows: list[dict], matches: list[dict]) -> list[dict]:
    base = sorted(rows, key=lambda r: (-r["win_pct"], -r["wins"], r["losses"]))

    # Break ties among equal (win_pct, wins) groups using head-to-head first.
    out: list[dict] = []
    i = 0
    while i < len(base):
        j = i
        key = (base[i]["win_pct"], base[i]["wins"])
        while j < len(base) and (base[j]["win_pct"], base[j]["wins"]) == key:
            j += 1
        group = base[i:j]
        if len(group) > 1:
            gids = {g["entry_id"] for g in group}
            for g in group:
                g["h2h"] = _h2h_score(g, gids, matches)[0]
            group.sort(key=lambda r: (
                -r["h2h"], -r["game_diff"], -r["point_diff"],
                -r["points_for"], -r["buchholz"], r["name"].lower()))
        else:
            group[0]["h2h"] = None
        out.extend(group)
        i = j

    for idx, r in enumerate(out, start=1):
        r["rank"] = idx
    return out


def compute_standings(event_id: int, stage: str | None = None, pool: str | None = None) -> list[dict]:
    entries = models.list_entries(event_id, active_only=False)
    matches = models.list_matches(event_id)
    if stage:
        matches = [m for m in matches if m["stage"] == stage]
    if pool:
        matches = [m for m in matches if m["pool"] == pool]
        entries = [e for e in entries if e["pool"] == pool]
    games = models.games_for_event(event_id)
    rows = _collect(event_id, matches, games, entries)
    table = _finalise(rows)
    return _sort_table(table, matches)


def pool_standings(event_id: int) -> dict[str, list[dict]]:
    entries = models.list_entries(event_id, active_only=False)
    pools = sorted({e["pool"] for e in entries if e["pool"]})
    return {p: compute_standings(event_id, stage=STAGE_POOL, pool=p) for p in pools}


# --------------------------------------------------------------------------
# Final placings for knockout formats
# --------------------------------------------------------------------------

def knockout_placings(event_id: int) -> list[dict]:
    """Order entries by how deep they went, then by their record."""
    ev = models.get_event(event_id)
    matches = models.list_matches(event_id)
    entries = {e["id"]: e for e in models.list_entries(event_id, active_only=False)}
    if not matches:
        return []

    knock_stages = {"main", STAGE_WB, STAGE_LB, STAGE_GF, STAGE_PLAYOFF}
    knock = [m for m in matches if m["stage"] in knock_stages]
    if not knock:
        return compute_standings(event_id)

    # Depth = the last round in which an entry appeared, weighted by bracket side.
    depth: dict[int, tuple] = {}
    for m in knock:
        weight = {STAGE_GF: 3, STAGE_WB: 2, STAGE_PLAYOFF: 2, "main": 2, STAGE_LB: 1}.get(m["stage"], 1)
        for side in (m["entry_a_id"], m["entry_b_id"]):
            if side is None:
                continue
            cur = (weight, m["round_no"])
            if side not in depth or cur > depth[side]:
                depth[side] = cur

    champion = None
    finals = [m for m in knock if m["stage"] == STAGE_GF] or \
             [m for m in knock if m["round_label"] and m["round_label"].endswith("Final")
              and "Semi" not in m["round_label"] and "3rd" not in m["round_label"]]
    if finals:
        last = max(finals, key=lambda m: (m["round_no"], m["id"]))
        if last["status"] in COUNTED:
            champion = last["winner_entry_id"]

    table = {r["entry_id"]: r for r in compute_standings(event_id)}
    rows = []
    for eid, e in entries.items():
        r = dict(table.get(eid, _blank(e)))
        r.setdefault("game_diff", 0)
        r.setdefault("point_diff", 0)
        r.setdefault("win_pct", 0.0)
        r["depth"] = depth.get(eid, (0, 0))
        r["is_champion"] = (eid == champion)
        rows.append(r)

    rows.sort(key=lambda r: (not r["is_champion"], -r["depth"][0], -r["depth"][1],
                             -r["win_pct"], -r["point_diff"], r["name"].lower()))
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return rows


def event_table(event_id: int) -> list[dict]:
    """The ranking view that suits this event's format."""
    ev = models.get_event(event_id)
    if not ev:
        return []
    if ev["format"] in ("single_elim", "double_elim"):
        return knockout_placings(event_id)
    if ev["format"] == "pool_playoff":
        has_playoff = any(m["stage"] == STAGE_PLAYOFF for m in models.list_matches(event_id))
        return knockout_placings(event_id) if has_playoff else compute_standings(event_id, stage=STAGE_POOL)
    return compute_standings(event_id)


def tournament_medals(tournament_id: int) -> list[dict]:
    """Podium across every event, for the tournament summary."""
    out = []
    for ev in models.list_events(tournament_id):
        table = event_table(ev["id"])
        done = ev["status"] == "complete"
        for r in table[:3]:
            out.append({
                "event": models.event_label(ev),
                "place": r["rank"], "name": r["name"],
                "record": f"{r['wins']}-{r['losses']}",
                "final": done,
            })
    return out


def player_leaderboard(tournament_id: int) -> list[dict]:
    """Every individual player across every event they entered."""
    players = {p["id"]: p for p in models.list_players(tournament_id)}
    agg = defaultdict(lambda: {"wins": 0, "losses": 0, "points_for": 0,
                               "points_against": 0, "events": set()})
    for ev in models.list_events(tournament_id):
        table = compute_standings(ev["id"])
        for r in table:
            e = r["entry"]
            for pid in filter(None, (e.get("player1_id"), e.get("player2_id"))):
                if pid not in players:
                    continue
                a = agg[pid]
                a["wins"] += r["wins"]
                a["losses"] += r["losses"]
                a["points_for"] += r["points_for"]
                a["points_against"] += r["points_against"]
                a["events"].add(models.event_label(ev))
    rows = []
    for pid, a in agg.items():
        played = a["wins"] + a["losses"]
        rows.append({
            "player": players[pid]["name"], "club": players[pid].get("club") or "",
            "events": ", ".join(sorted(a["events"])),
            "played": played, "wins": a["wins"], "losses": a["losses"],
            "win_pct": (a["wins"] / played) if played else 0.0,
            "point_diff": a["points_for"] - a["points_against"],
        })
    rows.sort(key=lambda r: (-r["wins"], -r["win_pct"], -r["point_diff"], r["player"].lower()))
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return rows
