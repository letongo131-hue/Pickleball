"""Simulates whole tournaments to prove the draw engine holds together.

Pure engine — no Streamlit needed to run this one."""

import random

from _testutil import check, finish, fresh_db

DB = fresh_db("engine")

from tourney import db, formats, models, standings  # noqa: E402
from tourney.constants import STATUS_BYE, STATUS_DONE, STATUS_VOID  # noqa: E402

RNG = random.Random(7)


def random_games(best_of, strength_a=0.5):
    need = best_of // 2 + 1
    wa = wb = 0
    games = []
    while wa < need and wb < need:
        if RNG.random() < strength_a:
            games.append((11, RNG.choice([2, 5, 7, 9])))
            wa += 1
        else:
            games.append((RNG.choice([3, 6, 8, 9]), 11))
            wb += 1
    return games


def play_all(event_id, actor="test"):
    """Play every ready match until nothing is left to play."""
    guard = 0
    while guard < 500:
        guard += 1
        open_ms = [m for m in models.list_matches(event_id)
                   if m["status"] in ("pending", "live") and models.match_ready(m)]
        if not open_ms:
            break
        for m in open_ms:
            fresh = models.get_match(m["id"])
            if fresh["status"] in (STATUS_DONE, STATUS_BYE, STATUS_VOID):
                continue
            models.submit_score(m["id"], random_games(fresh["best_of"]),
                                actor=actor, expected_version=fresh["version"])
    return guard


def make_event(tid, category, fmt, n_entries, **kw):
    eid = models.create_event(tid, category, fmt, actor="test", **kw)
    ev = models.get_event(eid)
    size = 1 if category in ("MS", "WS") else 2
    for i in range(n_entries):
        p1 = models.add_player(tid, f"{category}{i}a", gender="M", actor="test")
        p2 = models.add_player(tid, f"{category}{i}b", gender="F", actor="test") if size == 2 else None
        models.add_entry(eid, p1, p2, seed=i + 1, actor="test")
    return eid


print(f"Using test database: {DB}\n")
print("== Round robin (7 entries, odd count) ==")
t1 = models.create_tournament("Engine Test", venue="Court 1", actor="test")
rr = make_event(t1, "MS", "round_robin", 7)
formats.generate_draw(rr, actor="test")
ms = models.list_matches(rr)
check(len(ms) == 7 * 6 // 2, f"round robin creates 21 matches (got {len(ms)})")
pairs = {frozenset((m["entry_a_id"], m["entry_b_id"])) for m in ms}
check(len(pairs) == 21, "no duplicate pairings in round robin")
check(not models.rematch_audit(rr), "rematch audit is clean")
play_all(rr)
tbl = standings.compute_standings(rr)
check(len(tbl) == 7, "standings list all 7 entries")
check(all(r["played"] == 6 for r in tbl), "everyone played 6 matches")
check(sum(r["wins"] for r in tbl) == 21, "total wins equals total matches")
check([r["rank"] for r in tbl] == list(range(1, 8)), "ranks are 1..7 with no gaps")
check(models.get_event(rr)["status"] == "complete", "event marked complete")

print("\n== Single elimination (11 entries, byes) ==")
se = make_event(t1, "WS", "single_elim", 11)
formats.build_single_elim(se, actor="test", third_place=True)
ms = models.list_matches(se)
byes = [m for m in ms if m["status"] == STATUS_BYE]
check(len(byes) == 5, f"16-slot bracket with 11 entries gives 5 walkovers (got {len(byes)})")
play_all(se)
left = [m for m in models.list_matches(se) if m["status"] in ("pending", "live")]
check(not left, f"bracket fully resolved ({len(left)} left open)")
place = standings.knockout_placings(se)
check(place[0]["is_champion"], f"champion identified: {place[0]['name']}")
champ_losses = place[0]["losses"]
check(champ_losses == 0, f"single-elim champion has zero losses (got {champ_losses})")
third = [m for m in models.list_matches(se) if m["round_label"] == "3rd place"]
check(len(third) == 1 and third[0]["status"] == STATUS_DONE, "3rd place match played")

print("\n== Double elimination (8 entries) ==")
de = make_event(t1, "MD", "double_elim", 8)
formats.build_double_elim(de, actor="test")
ms = models.list_matches(de)
wb = [m for m in ms if m["stage"] == "wb"]
lb = [m for m in ms if m["stage"] == "lb"]
gf = [m for m in ms if m["stage"] == "gf"]
check(len(wb) == 7, f"winners bracket has 7 matches (got {len(wb)})")
check(len(lb) == 6, f"losers bracket has 6 matches (got {len(lb)})")
check(len(gf) == 1, "one grand final before any reset")
play_all(de)
left = [m for m in models.list_matches(de) if m["status"] in ("pending", "live")]
check(not left, f"double elim resolved ({len(left)} left open)")
final_rows = standings.knockout_placings(de)
champ = final_rows[0]
check(champ["is_champion"], f"double-elim champion: {champ['name']}")
check(champ["losses"] <= 1, f"champion lost at most once (got {champ['losses']})")
eliminated = [r for r in final_rows if r["losses"] >= 2]
check(len(eliminated) == 7, f"7 of 8 entries reached two losses (got {len(eliminated)})")

print("\n== Double elimination (13 entries, heavy byes) ==")
t2 = models.create_tournament("Bye Stress", actor="test")
de2 = make_event(t2, "MD", "double_elim", 13)
formats.build_double_elim(de2, actor="test")
play_all(de2)
left = [m for m in models.list_matches(de2) if m["status"] in ("pending", "live")]
check(not left, f"13-entry double elim resolved ({len(left)} open)")
rows2 = standings.knockout_placings(de2)
check(rows2[0]["is_champion"], f"champion found with byes: {rows2[0]['name']}")

print("\n== Swiss (9 entries, 5 rounds) ==")
sw = make_event(t2, "WS", "swiss", 9, swiss_rounds=5)
for expected in range(1, 6):
    rnd, repeated = formats.build_swiss_round(sw, actor="test")
    check(rnd == expected and not repeated, f"round {expected} paired with no forced rematch")
    play_all(sw)
ok, why = formats.swiss_round_ready(sw)
check(not ok, f"stops after 5 rounds: {why}")
dupes = models.rematch_audit(sw)
check(not dupes, f"no repeat pairings across 5 Swiss rounds (found {len(dupes)})")
byes = [m for m in models.list_matches(sw) if m["status"] == STATUS_BYE]
bye_winners = [m["winner_entry_id"] for m in byes]
check(len(byes) == 5, f"one bye per round with 9 entries (got {len(byes)})")
check(len(set(bye_winners)) == 5, "nobody received two byes")
tbl = standings.compute_standings(sw)
check(all("buchholz" in r for r in tbl), "Buchholz computed for Swiss")

print("\n== Pool play into playoffs (12 entries, 3 pools, top 2) ==")
pp = make_event(t2, "XD", "pool_playoff", 12, pool_count=3, advance_per_pool=2)
formats.build_pools(pp, pool_count=3, actor="test")
ents = models.list_entries(pp)
sizes = {}
for e in ents:
    sizes[e["pool"]] = sizes.get(e["pool"], 0) + 1
check(sorted(sizes.values()) == [4, 4, 4], f"pools evenly split: {sizes}")
try:
    formats.build_playoffs(pp, actor="test")
    check(False, "playoffs blocked before pools finish")
except models.RuleError:
    check(True, "playoffs blocked before pools finish")
play_all(pp)
check(formats.pools_complete(pp), "all pool matches finished")
formats.build_playoffs(pp, advance_per_pool=2, actor="test")
po = [m for m in models.list_matches(pp) if m["stage"] == "playoff"]
check(len(po) >= 4, f"playoff bracket built ({len(po)} matches)")
play_all(pp)
left = [m for m in models.list_matches(pp) if m["status"] in ("pending", "live")]
check(not left, "playoffs resolved")
check(standings.knockout_placings(pp)[0]["is_champion"], "pool→playoff champion found")

print("\n== Concurrency: two admins, one match ==")
t3 = models.create_tournament("Concurrency", actor="test")
cc = make_event(t3, "MS", "round_robin", 4)
formats.generate_draw(cc, actor="test")
m0 = models.list_matches(cc)[0]
stale_version = m0["version"]
models.submit_score(m0["id"], [(11, 4), (11, 6)], actor="Anna", expected_version=stale_version)
try:
    models.submit_score(m0["id"], [(5, 11), (7, 11)], actor="Ben", expected_version=stale_version)
    check(False, "stale save rejected")
except models.ConflictError as e:
    check("Anna" in str(e), "stale save rejected and names the other admin")
fresh = models.get_match(m0["id"])
models.submit_score(m0["id"], [(5, 11), (7, 11)], actor="Ben", expected_version=fresh["version"])
check(models.get_match(m0["id"])["winner_entry_id"] == m0["entry_b_id"],
      "corrected score applied once Ben reloaded")

print("\n== Fixture editing: rematch detection ==")
open_m = [m for m in models.list_matches(cc) if m["status"] == "pending"]
target = open_m[0]
opponent = target["entry_b_id"]
# In a round robin `opponent` is already scheduled against everyone, so any
# entry other than the two already in this fixture creates a repeat.
prior_opp = next(e["id"] for e in models.list_entries(cc)
                 if e["id"] not in (target["entry_a_id"], target["entry_b_id"]))
check(bool(models.have_met(cc, prior_opp, opponent, exclude_match=target["id"])),
      "test setup: chosen pair genuinely meet elsewhere")
try:
    models.set_match_entry(target["id"], "A", prior_opp, actor="test")
    check(False, "repeat matchup blocked")
except models.RuleError as e:
    check("already meet" in str(e), "repeat matchup blocked with explanation")
models.set_match_entry(target["id"], "A", prior_opp, actor="test", allow_rematch=True)
check(models.get_match(target["id"])["entry_a_id"] == prior_opp, "override allows the rematch")

print("\n== Score validation ==")
rule = {"target": 11, "win_by": 2, "cap": None}
cases = [
    ((11, 9), None, "11-9 is legal"),
    ((11, 10), "lead by 2", "11-10 rejected"),
    ((12, 10), None, "12-10 is legal"),
    ((13, 10), "leads by 2", "13-10 rejected"),
    ((9, 7), "reach 11", "9-7 rejected"),
    ((11, 11), "level", "11-11 rejected"),
]
for (a, b), expect, label in cases:
    err = models.validate_game(a, b, rule)
    hit = (expect is None and err is None) or (expect and err and expect in err)
    check(hit, f"{label} (got: {err})")
check(models.validate_match_scores([(11, 4), (11, 6), (11, 2)], 3, rule) is not None,
      "third game rejected when match already won 2-0")
check(models.validate_match_scores([(11, 4), (6, 11), (11, 9)], 3, rule) is None,
      "legitimate three-game match accepted")

print("\n== Reopen guard ==")
t4 = models.create_tournament("Reopen", actor="test")
re_ev = make_event(t4, "MS", "single_elim", 4)
formats.build_single_elim(re_ev, actor="test", third_place=False)
r1 = [m for m in models.list_matches(re_ev) if m["round_no"] == 1]
for m in r1:
    models.submit_score(m["id"], [(11, 5), (11, 3)], actor="test", expected_version=m["version"])
final = [m for m in models.list_matches(re_ev) if m["round_label"] == "Final"][0]
models.submit_score(final["id"], [(11, 8), (11, 9)], actor="test", expected_version=final["version"])
try:
    models.reopen_match(r1[0]["id"], actor="test")
    check(False, "cannot reopen a match whose next round is played")
except models.RuleError:
    check(True, "cannot reopen a match whose next round is played")
models.reopen_match(final["id"], actor="test")
models.reopen_match(r1[0]["id"], actor="test")
check(models.get_match(final["id"])["entry_a_id"] is None,
      "reopening pulls the entry back out of the next round")

print("\n== Local-test safety ==")
check(db.backend() == "sqlite", "tests run on SQLite, never a remote database")
check(db.sqlite_path() == DB, "and on the throwaway test file, not pickleball.db")

finish()
