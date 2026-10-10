"""Cross-event court scheduling: the same human in two categories at once.

Pure engine — no Streamlit needed to run this one."""

from _testutil import check, finish, fresh_db

DB = fresh_db("schedule")

from tourney import formats, models, schedule  # noqa: E402

# --- a tournament where people play more than one category ----------------
tid = models.create_tournament("Double Duty Open", venue="Main Hall", actor="test")

men = [models.add_player(tid, f"Man {i}", gender="M", actor="test") for i in range(8)]
women = [models.add_player(tid, f"Woman {i}", gender="F", actor="test") for i in range(8)]

ms = models.create_event(tid, "MS", "round_robin", actor="test")
for m in men:
    models.add_entry(ms, m, actor="test")

xd = models.create_event(tid, "XD", "round_robin", actor="test")
for i in range(8):
    models.add_entry(xd, men[i], women[i], actor="test")   # every man is in both events

formats.generate_draw(ms, actor="test")
formats.generate_draw(xd, actor="test")

for name in ("Court 1", "Court 2", "Court 3"):
    models.add_court(tid, name, actor="test")

print("== Setup ==")
ctx = schedule.tournament_context(tid)
check(len(ctx["events"]) == 2, "two events in the tournament")
check(len(schedule.ready_queue(ctx)) == 28 + 28, "56 matches ready across both events")
check(len(schedule.free_courts(tid, ctx)) == 3, "three courts free")

print("\n== Conflict detection ==")
# Put a Men's Singles match on court, then check the Mixed Doubles matches
# containing those same two men are all blocked.
ms_matches = models.list_matches(ms)
first = ms_matches[0]
men_on_court = schedule.match_players(first, ctx)
models.start_match(first["id"], actor="test", court="Court 1")

ctx = schedule.tournament_context(tid)
busy = schedule.busy_players(ctx)
check(set(busy) == men_on_court, f"{len(men_on_court)} player(s) marked busy")

xd_blocked = [m for m in models.list_matches(xd)
              if schedule.conflicts(m, ctx, busy)]
expected = [m for m in models.list_matches(xd)
            if schedule.match_players(m, ctx) & men_on_court]
check(len(xd_blocked) == len(expected) and len(xd_blocked) > 0,
      f"{len(xd_blocked)} mixed doubles match(es) correctly blocked by the singles match")
reason = schedule.conflicts(xd_blocked[0], ctx, busy)[0]
check("Man" in reason and "Men's Singles" in reason,
      f"block names the player and the clashing category: '{reason}'")

print("\n== Auto-call plan ==")
plan = schedule.plan_next(tid)
check(len(plan["assignments"]) == 2, f"fills both remaining courts (got {len(plan['assignments'])})")
courts_used = [a["court"] for a in plan["assignments"]]
check(courts_used == ["Court 2", "Court 3"], f"uses only free courts: {courts_used}")
check("Court 1" not in courts_used, "never reuses the occupied court")
check(all(not (schedule.match_players(a["match"], ctx) & men_on_court)
          for a in plan["assignments"]),
      "nobody already on Court 1 is called onto another court")

# The plan itself must not double-book anyone within the same pass.
ctx2 = schedule.tournament_context(tid)
seen = set(schedule.busy_players(ctx2))
overlap = False
for a in plan["assignments"]:
    ps = schedule.match_players(a["match"], ctx2)
    if ps & seen:
        overlap = True
    seen |= ps
check(not overlap, "no player appears twice within a single round of calls")
check(len(plan["blocked"]) > 0, f"{len(plan['blocked'])} match(es) held back with reasons")

print("\n== Committing the plan ==")
expected_on_court = set(men_on_court)
for a in plan["assignments"]:
    expected_on_court |= schedule.match_players(a["match"], ctx)
n = schedule.call_matches(tid, plan["assignments"], actor="test")
check(n == 2, f"{n} match(es) started")
ctx3 = schedule.tournament_context(tid)
check(len(schedule.occupied_courts(ctx3)) == 3, "all three courts now occupied")
check(schedule.free_courts(tid, ctx3) == [], "no courts left free")
plan2 = schedule.plan_next(tid)
check(plan2["assignments"] == [], "nothing more can be called with every court busy")
check(any("no court free" in b["reasons"] for b in plan2["blocked"]),
      "held-back list explains that courts are full")

print("\n== Closing a court ==")
c2 = [c for c in models.list_courts(tid) if c["name"] == "Court 2"][0]
try:
    models.delete_court(c2["id"], actor="test")
    check(False, "cannot delete a court with a live match")
except models.RuleError:
    check(True, "cannot delete a court with a live match")

print("\n== Player load ==")
rows = schedule.player_schedule(tid)
by_name = {r["player"]: r for r in rows}
some_man = by_name.get("Man 0")
check(some_man is not None and "Men's Singles" in some_man["events"]
      and "Mixed Doubles" in some_man["events"],
      "player load shows both categories a person is entered in")
on_court = {r["player"] for r in rows if r["on_court"]}
names = {ctx["players"][pid]["name"] for pid in expected_on_court}
check(on_court == names,
      f"every player in a live match is shown as on court ({len(on_court)} of {len(names)})")

print("\n== Freeing a court frees the players ==")
live = [m for m in models.list_matches(ms) if m["status"] == "live"]
models.submit_score(live[0]["id"], [(11, 5), (11, 7)], actor="test",
                    expected_version=models.get_match(live[0]["id"])["version"])
ctx4 = schedule.tournament_context(tid)
freed = schedule.free_courts(tid, ctx4)
check(freed == ["Court 1"], f"the finished match frees exactly its own court (got {freed})")
plan3 = schedule.plan_next(tid)
check(len(plan3["assignments"]) == 1, "exactly one new match can be called")
still_busy = set(schedule.busy_players(ctx4))
check(not (schedule.match_players(plan3["assignments"][0]["match"], ctx4) & still_busy),
      "the replacement match avoids everyone still on the other two courts")

print("\n== Tight field: the scheduler must idle a court rather than double-book ==")
tid2 = models.create_tournament("Tight Field", actor="test")
m2 = [models.add_player(tid2, f"TM {i}", gender="M", actor="test") for i in range(4)]
w2 = [models.add_player(tid2, f"TW {i}", gender="F", actor="test") for i in range(4)]
ms2 = models.create_event(tid2, "MS", "round_robin", actor="test")
for m in m2:
    models.add_entry(ms2, m, actor="test")
xd2 = models.create_event(tid2, "XD", "round_robin", actor="test")
for i in range(4):
    models.add_entry(xd2, m2[i], w2[i], actor="test")
formats.generate_draw(ms2, actor="test")
formats.generate_draw(xd2, actor="test")
for name in ("A", "B", "C"):
    models.add_court(tid2, name, actor="test")

tight = schedule.plan_next(tid2)
ctxt = schedule.tournament_context(tid2)
check(len(tight["assignments"]) == 2,
      f"only 2 of 3 courts can be filled with 4 men in both events "
      f"(got {len(tight['assignments'])})")
seen2 = set()
clash = False
for a in tight["assignments"]:
    ps = schedule.match_players(a["match"], ctxt)
    if ps & seen2:
        clash = True
    seen2 |= ps
check(not clash, "the two called matches share no player")
check(tight["courts_left"] == ["C"], f"third court left idle on purpose: {tight['courts_left']}")

finish()
