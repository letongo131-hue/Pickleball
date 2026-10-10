"""Draw builders for the five supported formats."""

from __future__ import annotations

import math
import random

from . import db, models
from .constants import (
    POOL_NAMES, STAGE_GF, STAGE_LB, STAGE_MAIN, STAGE_POOL, STAGE_PLAYOFF, STAGE_WB,
    STATUS_DONE, STATUS_BYE, STATUS_PENDING, STATUS_VOID,
)
from .i18n import tr
from .models import RuleError


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def seed_order(size: int) -> list[int]:
    """Standard bracket seeding: 1 meets 2 only in the final."""
    order = [1]
    while len(order) < size:
        m = len(order) * 2
        nxt = []
        for s in order:
            nxt.append(s)
            nxt.append(m + 1 - s)
        order = nxt
    return order


def knockout_label(matches_in_round: int, total_rounds: int, round_no: int) -> str:
    remaining = matches_in_round * 2
    if remaining == 2:
        return "Final"
    if remaining == 4:
        return "Semifinal"
    if remaining == 8:
        return "Quarterfinal"
    return f"Round of {remaining}"


def ordered_entries(event_id, shuffle_unseeded=True, rng=None) -> list[dict]:
    """Seeds first in order, then the rest (shuffled so the draw isn't alphabetical)."""
    entries = models.list_entries(event_id)
    seeded = [e for e in entries if e["seed"]]
    unseeded = [e for e in entries if not e["seed"]]
    seeded.sort(key=lambda e: e["seed"])
    if shuffle_unseeded:
        (rng or random).shuffle(unseeded)
    return seeded + unseeded


def _require_entries(entries, minimum=2):
    if len(entries) < minimum:
        raise RuleError(tr("Need at least {n} entries to build this draw.", n=minimum))


def round_robin_rounds(items: list) -> list[list[tuple]]:
    """Circle method. A None in a pair means that entry sits out that round."""
    ids = list(items)
    if len(ids) % 2:
        ids.append(None)
    n = len(ids)
    arr = ids[:]
    rounds = []
    for r in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a, b = arr[i], arr[n - 1 - i]
            if r % 2 and a is not None and b is not None:
                a, b = b, a          # alternate home/away so nobody always serves first
            pairs.append((a, b))
        rounds.append(pairs)
        arr = [arr[0], arr[-1]] + arr[1:-1]
    return rounds


# --------------------------------------------------------------------------
# Round robin
# --------------------------------------------------------------------------

def build_round_robin(event_id, entries=None, stage=STAGE_MAIN, pool=None, actor=None):
    ev = models.get_event(event_id)
    entries = entries if entries is not None else ordered_entries(event_id)
    _require_entries(entries)
    ids = [e["id"] for e in entries]
    rounds = round_robin_rounds(ids)
    for r, pairs in enumerate(rounds, start=1):
        mno = 1
        for a, b in pairs:
            if a is None or b is None:
                continue                     # odd entry count = a bye, no fixture needed
            label = f"Round {r}" if not pool else f"Pool {pool} · Round {r}"
            models.create_match(event_id, stage, r, mno, round_label=label, pool=pool,
                                entry_a_id=a, entry_b_id=b, best_of=ev["best_of"])
            mno += 1
    db.log(actor, ev["tournament_id"], "event", event_id, "draw", f"round_robin {len(entries)}")


# --------------------------------------------------------------------------
# Single elimination
# --------------------------------------------------------------------------

def build_single_elim(event_id, entries=None, stage=STAGE_MAIN, actor=None,
                      with_loser_links=False, third_place=False):
    ev = models.get_event(event_id)
    entries = entries if entries is not None else ordered_entries(event_id)
    _require_entries(entries)

    n = len(entries)
    size = 1 << max(1, math.ceil(math.log2(n)))
    rounds = int(math.log2(size))
    order = seed_order(size)
    slots = [entries[s - 1]["id"] if s <= n else None for s in order]

    ids: dict[tuple[int, int], int] = {}
    for r in range(1, rounds + 1):
        count = size >> r
        label = knockout_label(count, rounds, r)
        for i in range(count):
            ids[(r, i)] = models.create_match(event_id, stage, r, i + 1,
                                              round_label=label, best_of=ev["best_of"])

    for r in range(1, rounds):
        for i in range(size >> r):
            models.link(ids[(r, i)], next_match_id=ids[(r + 1, i // 2)],
                        next_slot="A" if i % 2 == 0 else "B")

    for i in range(size // 2):
        a, b = slots[2 * i], slots[2 * i + 1]
        db.update("matches", ids[(1, i)], {
            "entry_a_id": a, "entry_b_id": b,
            "a_void": 0 if a else 1, "b_void": 0 if b else 1,
        })

    if third_place and rounds >= 2:
        tp = models.create_match(event_id, stage, rounds, 2,
                                 round_label="3rd place", best_of=ev["best_of"])
        for i in range(2):
            models.link(ids[(rounds - 1, i)], loser_next_match_id=tp,
                        loser_next_slot="A" if i == 0 else "B")

    models.resolve_byes(event_id)
    db.log(actor, ev["tournament_id"], "event", event_id, "draw", f"single_elim {n}")
    return ids, rounds, size


# --------------------------------------------------------------------------
# Double elimination
# --------------------------------------------------------------------------

def build_double_elim(event_id, entries=None, actor=None):
    """Winners bracket + losers bracket + grand final.

    For a bracket of size N = 2^n the losers side has 2(n-1) rounds. Odd LB
    rounds pair survivors against each other; even LB rounds take that round's
    winners against the players just knocked out of the winners bracket. The
    drop order is reversed on alternate rounds so an entry is less likely to
    immediately replay whoever beat them.
    """
    ev = models.get_event(event_id)
    entries = entries if entries is not None else ordered_entries(event_id)
    _require_entries(entries, 3)

    n_entries = len(entries)
    size = 1 << max(1, math.ceil(math.log2(n_entries)))
    n = int(math.log2(size))
    order = seed_order(size)
    slots = [entries[s - 1]["id"] if s <= n_entries else None for s in order]

    # Winners bracket
    wb: dict[tuple[int, int], int] = {}
    for r in range(1, n + 1):
        count = size >> r
        label = "WB Final" if count == 1 else f"WB {knockout_label(count, n, r)}"
        for i in range(count):
            wb[(r, i)] = models.create_match(event_id, STAGE_WB, r, i + 1,
                                             round_label=label, best_of=ev["best_of"])
    for r in range(1, n):
        for i in range(size >> r):
            models.link(wb[(r, i)], next_match_id=wb[(r + 1, i // 2)],
                        next_slot="A" if i % 2 == 0 else "B")

    # Losers bracket
    lb_rounds = max(0, 2 * (n - 1))
    lb: dict[tuple[int, int], int] = {}
    lb_size: dict[int, int] = {}
    for k in range(1, lb_rounds + 1):
        j = (k + 1) // 2
        count = max(1, size >> (j + 1))
        lb_size[k] = count
        label = "LB Final" if k == lb_rounds else f"LB Round {k}"
        for i in range(count):
            lb[(k, i)] = models.create_match(event_id, STAGE_LB, k, i + 1,
                                             round_label=label, best_of=ev["best_of"])
    for k in range(1, lb_rounds):
        cur, nxt = lb_size[k], lb_size[k + 1]
        for i in range(cur):
            if cur == nxt:
                models.link(lb[(k, i)], next_match_id=lb[(k + 1, i)], next_slot="A")
            else:
                models.link(lb[(k, i)], next_match_id=lb[(k + 1, i // 2)],
                            next_slot="A" if i % 2 == 0 else "B")

    # WB round 1 losers fill both slots of LB round 1
    if lb_rounds:
        for i in range(size // 2):
            models.link(wb[(1, i)], loser_next_match_id=lb[(1, i // 2)],
                        loser_next_slot="A" if i % 2 == 0 else "B")
    # WB round r >= 2 losers drop into slot B of LB round 2r-2
    for r in range(2, n + 1):
        k = 2 * r - 2
        if k > lb_rounds:
            break
        count = size >> r
        targets = list(range(lb_size[k]))
        if r % 2 == 0:
            targets.reverse()
        for i in range(count):
            models.link(wb[(r, i)], loser_next_match_id=lb[(k, targets[i % len(targets)])],
                        loser_next_slot="B")

    # Grand final
    gf = models.create_match(event_id, STAGE_GF, n + 1, 1,
                             round_label="Grand Final", best_of=ev["best_of"])
    models.link(wb[(n, 0)], next_match_id=gf, next_slot="A")
    if lb_rounds:
        models.link(lb[(lb_rounds, 0)], next_match_id=gf, next_slot="B")
    else:
        db.update("matches", gf, {"b_void": 1})

    for i in range(size // 2):
        a, b = slots[2 * i], slots[2 * i + 1]
        db.update("matches", wb[(1, i)], {
            "entry_a_id": a, "entry_b_id": b,
            "a_void": 0 if a else 1, "b_void": 0 if b else 1,
        })

    models.resolve_byes(event_id)
    db.log(actor, ev["tournament_id"], "event", event_id, "draw", f"double_elim {n_entries}")


# --------------------------------------------------------------------------
# Pool play → playoffs
# --------------------------------------------------------------------------

def build_pools(event_id, pool_count=None, actor=None, rng=None, method="seed"):
    ev = models.get_event(event_id)
    entries = models.list_entries(event_id)
    _require_entries(entries, 4)

    if method == "manual":
        if not all(e["pool"] for e in entries):
            raise RuleError(tr("Drag every entry into a pool (Draw section of Event entries) "
                               "before generating a manual draw."))
        buckets_by_letter: dict[str, list[dict]] = {}
        for e in entries:
            buckets_by_letter.setdefault(e["pool"], []).append(e)
        buckets = [buckets_by_letter[k] for k in sorted(buckets_by_letter)]
    else:
        entries = ordered_entries(event_id, rng=rng)   # already shuffled if method == "random"
        pool_count = pool_count or ev["pool_count"] or 2
        pool_count = max(1, min(pool_count, len(entries) // 2, len(POOL_NAMES)))
        # Snake the seeds across pools so each pool gets a comparable spread.
        buckets = [[] for _ in range(pool_count)]
        for i, e in enumerate(entries):
            row, col = divmod(i, pool_count)
            idx = col if row % 2 == 0 else pool_count - 1 - col
            buckets[idx].append(e)

    for p, group in enumerate(buckets):
        if not group:
            continue
        letter = group[0]["pool"] if method == "manual" else POOL_NAMES[p]
        for e in group:
            db.update("entries", e["id"], {"pool": letter})
        if len(group) < 2:
            continue   # a pool of one auto-qualifies; nothing to schedule
        build_round_robin(event_id, entries=group, stage=STAGE_POOL, pool=letter, actor=actor)
    db.log(actor, ev["tournament_id"], "event", event_id, "draw",
           f"pools {len(buckets)}x{len(entries)} ({method})")


def pools_complete(event_id) -> bool:
    rows = [m for m in models.list_matches(event_id) if m["stage"] == STAGE_POOL]
    return bool(rows) and all(m["status"] in (STATUS_DONE, STATUS_BYE, STATUS_VOID) for m in rows)


def build_playoffs(event_id, advance_per_pool=None, actor=None):
    from .standings import pool_standings

    ev = models.get_event(event_id)
    if any(m["stage"] == STAGE_PLAYOFF for m in models.list_matches(event_id)):
        raise RuleError(tr("Playoffs have already been generated."))
    if not pools_complete(event_id):
        raise RuleError(tr("Finish every pool match before generating the playoffs."))
    adv = advance_per_pool or ev["advance_per_pool"] or 2

    tables = pool_standings(event_id)          # {"A": [row, row, ...], ...}
    qualified: list[tuple[int, int, str, dict]] = []
    for letter, rows in tables.items():
        for place, row in enumerate(rows[:adv], start=1):
            qualified.append((place, row["rank"], letter, row))
    if len(qualified) < 2:
        raise RuleError(tr("Not enough qualifiers for a playoff bracket."))

    # Seed by finishing position first (all pool winners, then all runners-up),
    # and within a position by win rate then point differential.
    qualified.sort(key=lambda q: (q[0], -q[3]["win_pct"], -q[3]["point_diff"], q[2]))
    seeded = []
    for i, (place, _, letter, row) in enumerate(qualified, start=1):
        e = dict(row["entry"])
        e["seed"] = i
        e["_pool_place"] = f"{letter}{place}"
        seeded.append(e)

    build_single_elim(event_id, entries=seeded, stage=STAGE_PLAYOFF, actor=actor,
                      third_place=len(seeded) >= 4)
    db.execute("UPDATE matches SET round_label = 'Playoff ' || round_label "
               "WHERE event_id = ? AND stage = ?", (event_id, STAGE_PLAYOFF))
    db.log(actor, ev["tournament_id"], "event", event_id, "draw", f"playoffs top{adv}")


# --------------------------------------------------------------------------
# Swiss
# --------------------------------------------------------------------------

def swiss_rounds_played(event_id) -> int:
    rows = models.list_matches(event_id)
    return max((m["round_no"] for m in rows), default=0)


def swiss_round_ready(event_id) -> tuple[bool, str]:
    rows = models.list_matches(event_id)
    if not rows:
        return True, ""
    last = max(m["round_no"] for m in rows)
    open_now = [m for m in rows if m["round_no"] == last
                and m["status"] not in (STATUS_DONE, STATUS_BYE, STATUS_VOID)]
    if open_now:
        return False, tr("Round {r} still has {n} match(es) to finish.", r=last, n=len(open_now))
    ev = models.get_event(event_id)
    if last >= (ev["swiss_rounds"] or 5):
        return False, tr("All {n} scheduled Swiss rounds are complete.", n=last)
    return True, ""


def _pair_swiss(order: list[int], played: set[frozenset]) -> list[tuple[int, int]] | None:
    """Greedy pairing with backtracking: strongest available plays the nearest
    opponent they have not met yet."""
    if not order:
        return []
    if len(order) % 2:
        return None
    first, rest = order[0], order[1:]
    for i, cand in enumerate(rest):
        if frozenset((first, cand)) in played:
            continue
        remainder = rest[:i] + rest[i + 1:]
        sub = _pair_swiss(remainder, played)
        if sub is not None:
            return [(first, cand)] + sub
    return None


def build_swiss_round(event_id, actor=None, allow_rematch_fallback=True):
    from .standings import compute_standings

    ev = models.get_event(event_id)
    ok, why = swiss_round_ready(event_id)
    if not ok:
        raise RuleError(why)

    entries = models.list_entries(event_id)
    _require_entries(entries)
    rnd = swiss_rounds_played(event_id) + 1

    if rnd == 1:
        order = [e["id"] for e in ordered_entries(event_id)]
        byes: set[int] = set()
    else:
        table = compute_standings(event_id)
        order = [r["entry"]["id"] for r in table]
        byes = {m["winner_entry_id"] for m in models.list_matches(event_id)
                if m["status"] == STATUS_BYE and m["winner_entry_id"]}

    bye_entry = None
    if len(order) % 2:
        # Bye goes to the lowest-ranked entry who has not had one yet.
        for cand in reversed(order):
            if cand not in byes:
                bye_entry = cand
                break
        bye_entry = bye_entry or order[-1]
        order = [x for x in order if x != bye_entry]

    played = set()
    for m in models.list_matches(event_id):
        if m["entry_a_id"] and m["entry_b_id"] and m["status"] != STATUS_VOID:
            played.add(frozenset((m["entry_a_id"], m["entry_b_id"])))

    pairs = _pair_swiss(order, played)
    repeated = False
    if pairs is None:
        if not allow_rematch_fallback:
            raise RuleError(tr("No rematch-free pairing exists for this round."))
        pairs = [(order[i], order[i + 1]) for i in range(0, len(order) - 1, 2)]
        repeated = True

    for i, (a, b) in enumerate(pairs, start=1):
        models.create_match(event_id, STAGE_MAIN, rnd, i, round_label=f"Round {rnd}",
                            entry_a_id=a, entry_b_id=b, best_of=ev["best_of"])
    if bye_entry:
        mid = models.create_match(event_id, STAGE_MAIN, rnd, len(pairs) + 1,
                                  round_label=f"Round {rnd}", entry_a_id=bye_entry,
                                  best_of=ev["best_of"])
        db.update("matches", mid, {"b_void": 1})
        models.resolve_byes(event_id)

    db.log(actor, ev["tournament_id"], "event", event_id, "draw", f"swiss round {rnd}")
    return rnd, repeated


# --------------------------------------------------------------------------
# Custom mode — the admin builds the bracket by hand, match by match
# --------------------------------------------------------------------------
# Round 1 pairs real entries directly. Every later round starts as empty
# placeholder matches; the admin then points each earlier match's winner —
# and its loser too, if they want that side to keep playing — at a specific
# slot in one of those placeholders. `models.propagate()` (already used by
# every built-in format) does the rest once results come in, so a custom
# bracket is just a hand-wired graph of the exact same primitives.

def custom_build_round1(event_id, pairs: list[tuple[int, int]], actor=None):
    """`pairs` is the admin's exact round-1 matchups, in order, from
    dragging entries together — nothing here decides who plays whom."""
    ev = models.get_event(event_id)
    if not ev:
        raise RuleError(tr("Event not found."))
    if models.list_matches(event_id):
        raise RuleError(tr("This event already has matches. Clear the draw first."))
    if not pairs:
        raise RuleError(tr("Pair up at least one match before creating round 1."))
    for i, (a, b) in enumerate(pairs, start=1):
        models.create_match(event_id, STAGE_MAIN, 1, i, round_label="Round 1",
                            entry_a_id=a, entry_b_id=b, best_of=ev["best_of"])
    models.set_draw_method(event_id, "custom", actor=actor)
    db.log(actor, ev["tournament_id"], "event", event_id, "draw",
           f"custom round 1 ({len(pairs)} matches)")
    models._refresh_event_status(event_id)


def custom_add_round(event_id, round_no, count, label=None, actor=None) -> list[int]:
    """Adds `count` empty placeholder matches for a new round — wire earlier
    matches' winners/losers into them with `custom_wire` once they exist."""
    ev = models.get_event(event_id)
    if not ev:
        raise RuleError(tr("Event not found."))
    if count < 1:
        raise RuleError(tr("Add at least one match."))
    existing = [m for m in models.list_matches(event_id) if m["round_no"] == round_no]
    start_no = len(existing) + 1
    ids = []
    for i in range(count):
        mid = models.create_match(event_id, STAGE_MAIN, round_no, start_no + i,
                                  round_label=label or f"Round {round_no}",
                                  best_of=ev["best_of"])
        ids.append(mid)
    db.log(actor, ev["tournament_id"], "event", event_id, "draw",
           f"custom round {round_no} +{count} match(es)")
    models._refresh_event_status(event_id)
    return ids


def custom_wire(match_id, winner_to: tuple[int, str] | None = None,
                loser_to: tuple[int, str] | None = None, actor=None):
    """Point this match's winner (and optionally its loser) at a
    (match_id, 'A'|'B') slot in a later round. Pass None for either side to
    leave it unrouted — a winner with no route is the bracket's champion; a
    loser with no route is simply eliminated.

    If the match has already been played — deciding where a result goes
    only after seeing it is a completely normal way to build a custom
    bracket — the winner/loser are sent on their way immediately instead of
    waiting for a `_finish_match` that already happened.
    """
    m = models.get_match(match_id)
    if not m:
        raise RuleError(tr("Match not found."))
    old_win = (m["next_match_id"], m["next_slot"]) if m["next_match_id"] else None
    old_lose = (m["loser_next_match_id"], m["loser_next_slot"]) if m["loser_next_match_id"] else None

    db.update("matches", match_id, {
        "next_match_id": winner_to[0] if winner_to else None,
        "next_slot": winner_to[1] if winner_to else None,
        "loser_next_match_id": loser_to[0] if loser_to else None,
        "loser_next_slot": loser_to[1] if loser_to else None,
    })
    db.log(actor, None, "match", match_id, "route",
           f"winner→{winner_to or '—'} loser→{loser_to or '—'}")

    if m["status"] in (STATUS_DONE, STATUS_BYE):
        # Re-routing after the fact can point somewhere new — clear the
        # entry out of wherever the old routing had already placed it (if
        # that slot hasn't itself been played) so nothing is left behind.
        if old_win and old_win != winner_to:
            _clear_routed_slot(*old_win)
        if old_lose and old_lose != loser_to:
            _clear_routed_slot(*old_lose)
        models.propagate(match_id)


def _clear_routed_slot(target_match_id, slot):
    col = "entry_a_id" if slot == "A" else "entry_b_id"
    db.execute(f"UPDATE matches SET {col} = NULL WHERE id = ? AND status = 'pending'",
              (target_match_id,))


# --------------------------------------------------------------------------
# Entry point used by the UI
# --------------------------------------------------------------------------

def generate_draw(event_id, actor=None, method="seed", **kwargs):
    """`method` decides how entries are ordered before the draw is built:
    - "seed":   use each entry's seed number as-is (unseeded entries fill the
                remaining spots in random order) — today's default.
    - "random": ignore any seed numbers and draw a fresh random order for
                every entry, recorded as their new seed so it's visible.
    - "manual": the draw already happened outside the app — every entry must
                already have an explicit position (a seed, or for pool play
                a pool) set on the Draws & standings page; nothing here is
                computed, only recorded.
    - "custom": the admin builds the bracket by hand, round by round, on the
                Draws & standings page — this function is not used for that;
                see `custom_build_round1` / `custom_add_round` / `custom_wire`.
    """
    ev = models.get_event(event_id)
    if not ev:
        raise RuleError(tr("Event not found."))
    if method == "custom":
        raise RuleError(tr("Custom brackets are built round by round in the Draw section, "
                           "not generated here."))
    if models.list_matches(event_id):
        raise RuleError(tr("This event already has a draw. Clear it first."))
    fmt = ev["format"]

    if method == "random":
        entries = models.list_entries(event_id)
        shuffled = entries[:]
        random.shuffle(shuffled)
        for i, e in enumerate(shuffled, start=1):
            db.update("entries", e["id"], {"seed": i})
    elif method == "manual" and fmt != "pool_playoff":
        entries = models.list_entries(event_id)
        if not all(e["seed"] for e in entries):
            raise RuleError(tr("Every entry needs a recorded position before generating a "
                               "manual draw — record the order in the Draw section first."))

    if fmt == "round_robin":
        build_round_robin(event_id, actor=actor)
    elif fmt == "single_elim":
        build_single_elim(event_id, actor=actor, third_place=kwargs.get("third_place", True))
    elif fmt == "double_elim":
        build_double_elim(event_id, actor=actor)
    elif fmt == "pool_playoff":
        build_pools(event_id, pool_count=kwargs.get("pool_count"), actor=actor, method=method)
    elif fmt == "swiss":
        build_swiss_round(event_id, actor=actor)
    else:
        raise RuleError(tr("Unsupported format {x}", x=fmt))
    models.set_draw_method(event_id, method, actor=actor)
    db.log(actor, ev["tournament_id"], "event", event_id, "draw_method", method)
    models._refresh_event_status(event_id)
