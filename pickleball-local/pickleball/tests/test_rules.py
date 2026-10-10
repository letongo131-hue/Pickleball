"""Pickleball scoring rules: the pure rules engine, then the same rules driven
through the database the way the referee view drives them.

Pure engine — no Streamlit needed to run this one."""

from _testutil import check, finish, fresh_db

DB = fresh_db("rules")

from tourney import formats, models, rules  # noqa: E402
from tourney.constants import SCORING_PRESETS  # noqa: E402

TO11 = SCORING_PRESETS["11_rally_2"]      # to 11, win by 2
TO21 = SCORING_PRESETS["21_rally_2"]


def play(state, score, winners, rule=TO11, deciding=False):
    events = []
    for w in winners:
        state, score, ev = rules.apply_rally(state, score, w, rule, deciding)
        events.append(ev)
    return state, score, events


print("== Side-out doubles: the 0-0-2 start ==")
s = rules.new_game(doubles=True, first_serving="a", right={"a": 0, "b": 1})
sc = (0, 0)
check(rules.score_call(s, sc) == "0 – 0 – 2", "game opens with the call 0-0-2")
check(s["server_idx"] == 0 and rules.server_court(s, sc) == "right",
      "first server is the player in the right court")

s1, sc1, ev = play(s, sc, ["a"])
check(sc1 == (1, 0) and ev[0] == ["point"], "serving side wins the rally: point")
check(rules.score_call(s1, sc1) == "1 – 0 – 2", "call becomes 1-0-2")
check(s1["server_idx"] == 0 and rules.server_court(s1, sc1) == "left",
      "same server keeps serving, now from the left court (switched with partner)")

s2, sc2, ev = play(s1, sc1, ["b"])
check(ev[0] == ["side_out"] and s2["serving"] == "b",
      "first serving side only gets one server: losing the rally is a side out")
check(sc2 == (1, 0), "receiving side does NOT score in side-out scoring")
check(rules.score_call(s2, sc2) == "0 – 1 – 1", "call is from the new server's side: 0-1-1")
check(s2["server_idx"] == 1 and rules.server_court(s2, sc2) == "right",
      "new serving side starts with whoever is in their right court")

s3, sc3, ev = play(s2, sc2, ["a"])
check(ev[0] == ["second_server"] and s3["serving"] == "b" and s3["server_no"] == 2,
      "server 1 loses: partner becomes server 2, no side out yet")
check(s3["server_idx"] == 0 and rules.server_court(s3, sc3) == "left",
      "server 2 serves from wherever they are standing (left court)")
check(rules.score_call(s3, sc3) == "0 – 1 – 2", "call is 0-1-2")

s4, sc4, ev = play(s3, sc3, ["a"])
check(ev[0] == ["side_out"] and s4["serving"] == "a" and s4["server_no"] == 1,
      "server 2 loses: side out back to A as server 1")
check(s4["server_idx"] == s4["right"]["a"], "A's server 1 is the player now in A's right court")
check(rules.position_warning(s4, sc4) is None, "positions match the scores (odd score, starter on left)")

print("\n== Side-out singles ==")
g = rules.new_game(doubles=False, first_serving="a")
check(rules.score_call(g, (0, 0)) == "0 – 0", "singles call has no server number")
g, sc, _ = play(g, (0, 0), ["a"])
check(rules.server_court(g, sc) == "left", "server on 1 (odd) serves from the left")
g, sc, _ = play(g, sc, ["a"])
check(rules.server_court(g, sc) == "right", "server on 2 (even) serves from the right")
g, sc, ev = play(g, sc, ["b"])
check(ev[0] == ["side_out"] and g["serving"] == "b" and sc == (2, 0),
      "singles: losing the rally is an immediate side out, no point")
check(rules.server_court(g, sc) == "right", "new server on 0 (even) serves from the right")

print("\n== Rally scoring ==")
r = rules.new_game(doubles=True, system=rules.RALLY, first_serving="a", right={"a": 0, "b": 0})
check(rules.score_call(r, (0, 0)) == "0 – 0", "rally scoring: no server number, no 0-0-2")
r, sc, ev = play(r, (0, 0), ["b"], )
check(sc == (0, 1) and ev[0] == ["point", "side_out"],
      "receiving side wins: they score AND take the serve")
check(r["server_idx"] == 1, "on an odd score the player in the left court serves")
r, sc, _ = play(r, sc, ["b"])
check(sc == (0, 2) and r["server_idx"] == 1 and rules.server_court(r, sc) == "right",
      "serving side scores: server switches to the right on an even score")

print("\n== Game end, win by 2, caps ==")
s = rules.new_game(doubles=False, first_serving="a")
st, sc, ev = play(s, (10, 9), ["a"])
check(st["game_over"] == "a" and "game_over" in ev[-1], "11-9 ends the game")
st, sc, ev = play(s, (10, 10), ["a"])
check(st["game_over"] is None, "11-10 does not end a win-by-2 game")
st, sc, ev = play(st, sc, ["a"])
check(st["game_over"] == "a" and sc == (12, 10), "12-10 does")
try:
    rules.apply_rally(st, sc, "a", TO11)
    check(False, "no rallies after the game is over")
except ValueError:
    check(True, "no rallies after the game is over")
first11 = SCORING_PRESETS["11_first"]
st, sc, _ = play(rules.new_game(doubles=False), (10, 10), ["a"], rule=first11)
check(st["game_over"] == "a", "'first to 11' ends at 11-10")
cap = SCORING_PRESETS["11_cap_15"]
st, sc, _ = play(rules.new_game(doubles=False), (14, 14), ["a"], rule=cap)
check(st["game_over"] == "a" and sc == (15, 14), "a capped game ends at the cap, 15-14")

print("\n== Game point / match point ==")
s = rules.new_game(doubles=False, first_serving="a")
check(rules.game_point_for(s, (10, 5), TO11) == ["a"], "serving side on 10-5 has game point")
s_b = rules.new_game(doubles=False, first_serving="b")
check(rules.game_point_for(s_b, (10, 5), TO11) == [],
      "side-out scoring: the RECEIVING side on 10 can't win on the next rally")
r = rules.new_game(doubles=False, system=rules.RALLY, first_serving="b")
check(rules.game_point_for(r, (10, 5), TO11) == ["a"],
      "rally scoring: the receiving side on 10 does have game point")

print("\n== Switching ends ==")
s = rules.new_game(doubles=False, first_serving="a")
st, sc, ev = play(s, (5, 2), ["a"], deciding=True)
check("switch_ends" in ev[0] and st["a_left"] is False, "deciding game: switch ends at 6")
st, sc, ev = play(st, sc, ["a"], deciding=True)
check("switch_ends" not in ev[0] and st["a_left"] is False, "...only once")
st, sc, ev = play(s, (5, 2), ["a"], deciding=False)
check("switch_ends" not in ev[0], "no mid-game switch in a non-deciding game")
st, sc, ev = play(rules.new_game(doubles=False), (10, 3), ["a"], rule=TO21, deciding=True)
check("switch_ends" in ev[0], "game to 21: switch at 11")
check(rules.is_deciding_game({"a": 1, "b": 1}, 3), "game 3 at 1-1 is the decider in a best of 3")
check(not rules.is_deciding_game({"a": 1, "b": 0}, 3), "game 2 is not")
check(rules.is_deciding_game({"a": 0, "b": 0}, 1), "a one-game match is its own decider")

print("\n== Timeouts and next game ==")
s = rules.new_game(doubles=True, first_serving="a", right={"a": 1, "b": 0})
s = rules.use_timeout(rules.use_timeout(s, "a", TO11), "a", TO11)
try:
    rules.use_timeout(s, "a", TO11)
    check(False, "a third timeout in a game to 11 is refused")
except ValueError:
    check(True, "a third timeout in a game to 11 is refused")
check(rules.timeouts_allowed(TO21) == 3, "games to 21 get three timeouts")
n = rules.next_game(s)
check(n["first_serving"] == "b" and n["a_left"] is False and n["timeouts"] == {"a": 0, "b": 0},
      "next game: the side that received first serves first, ends change, timeouts reset")
check(n["server_no"] == 2 and n["right"] == {"a": 1, "b": 0}, "next game restarts at 0-0-2 in starting positions")

# --------------------------------------------------------------------------
print("\n== Through the database: a doubles match refereed rally by rally ==")
tid = models.create_tournament("Rules Cup", actor="t")
men = [models.add_player(tid, f"M{i}", gender="M", actor="t") for i in range(4)]
md = models.create_event(tid, "MD", "single_elim", best_of=3, actor="t")
ea = models.add_entry(md, men[0], men[1], actor="t")
eb = models.add_entry(md, men[2], men[3], actor="t")
formats.generate_draw(md, actor="t")
m = models.list_matches(md)[0]
a_side = "a" if m["entry_a_id"] == ea else "b"
models.start_match(m["id"], actor="ref", court="Court 1", first_serving="b", right={"a": 1, "b": 0})
st = models.serve_state(models.get_match(m["id"]))
check(st["serving"] == "b" and st["server_no"] == 2 and st["right"] == {"a": 1, "b": 0},
      "start_match records who serves first and who starts on the right")
check(models.side_players(m)["a"][0]["id"] is not None and len(models.side_players(m)["b"]) == 2,
      "side_players lists both registered players on each side")

ev = models.record_rally(m["id"], "a", actor="ref")
mm = models.get_match(m["id"])
check(ev == ["side_out"] and (mm["cur_a"], mm["cur_b"]) == (0, 0),
      "rally to the receivers at 0-0-2 is a side out, no point")
models.record_rally(m["id"], "a", actor="ref")
mm = models.get_match(m["id"])
check((mm["cur_a"], mm["cur_b"]) == (1, 0), "then A scores on their serve")
models.call_timeout(m["id"], "b", actor="ref")
check(models.serve_state(models.get_match(m["id"]))["timeouts"]["b"] == 1, "timeout recorded")
models.undo_rally(m["id"], actor="ref")
check(models.serve_state(models.get_match(m["id"]))["timeouts"]["b"] == 0, "undo removes the timeout")
models.undo_rally(m["id"], actor="ref")
mm = models.get_match(m["id"])
check((mm["cur_a"], mm["cur_b"]) == (0, 0) and models.serve_state(mm)["serving"] == "a",
      "undo restores the exact score and serve state before the rally")
try:
    models.setup_serve(m["id"], "a", actor="ref")
    check(False, "serve setup is locked once rallies have been played")
except models.RuleError:
    check(True, "serve setup is locked once rallies have been played")

# Play game 1 to 11-0 for A.
while not models.serve_state(models.get_match(m["id"]))["game_over"]:
    models.record_rally(m["id"], "a", actor="ref")
mm = models.get_match(m["id"])
check((mm["cur_a"], mm["cur_b"]) == (11, 0) and models.serve_state(mm)["game_over"] == "a",
      "11-0: the engine calls the game over")
try:
    models.record_rally(m["id"], "a", actor="ref")
    check(False, "no more rallies until the game is confirmed")
except models.RuleError:
    check(True, "no more rallies until the game is confirmed")
finished = models.confirm_current_game(m["id"], actor="ref")
mm = models.get_match(m["id"])
st = models.serve_state(mm)
check(not finished and (mm["cur_a"], mm["cur_b"]) == (0, 0), "game 1 locked in, game 2 starts at 0-0")
check(st["first_serving"] == "a" and st["a_left"] is False and st["server_no"] == 2,
      "game 2: B served first in game 1, so A serves first; ends switched; 0-0-2")
models.undo_last_game(m["id"], actor="ref")
mm = models.get_match(m["id"])
check((mm["cur_a"], mm["cur_b"]) == (11, 0) and models.serve_state(mm)["game_over"] == "a",
      "undo last game restores 11-0 and the game-over state")
models.confirm_current_game(m["id"], actor="ref")
while models.get_match(m["id"])["status"] == "live":
    if models.serve_state(models.get_match(m["id"]))["game_over"]:
        models.confirm_current_game(m["id"], actor="ref")
    else:
        models.record_rally(m["id"], "a", actor="ref")
mm = models.get_match(m["id"])
check(mm["status"] == "done" and mm["winner_entry_id"] == mm["entry_a_id"]
      and len(models.get_games(m["id"])) == 2, "A wins 2-0 and the match finishes")

print("\n== Manual corrections still respect game end ==")
mid = models.start_quick_match("Lan", "Mai", scoring="11_rally_2", best_of=1, actor="ref")["id"]
models.start_match(mid, actor="ref")
for _ in range(9):
    models.adjust_point(mid, "a", 1, actor="ref")
models.adjust_point(mid, "b", 1, actor="ref")
models.adjust_point(mid, "a", 1, actor="ref")
models.adjust_point(mid, "a", 1, actor="ref")
check(models.serve_state(models.get_match(mid))["game_over"] == "a", "a corrected 11-1 is recognised as game over")
models.adjust_point(mid, "a", -1, actor="ref")
check(models.serve_state(models.get_match(mid))["game_over"] is None, "taking a point back reopens the game")

print("\n== Quick match doubles and rally scoring ==")
q = models.start_quick_match("An", "Binh", partner_a="Chi", partner_b="Dung",
                             scoring_system=rules.RALLY, actor="ref")
check(models.is_doubles(q), "a quick match with partners is doubles")
check([p["name"] for p in models.side_players(q)["a"]] == ["An", "Chi"], "partners kept in order")
models.start_match(q["id"], actor="ref")
models.record_rally(q["id"], "b", actor="ref")
qm = models.get_match(q["id"])
check((qm["cur_a"], qm["cur_b"]) == (0, 1), "quick match honours rally scoring")

print("\n== Renaming a player updates every event they're in ==")
tid2 = models.create_tournament("Rename Cup", actor="t")
pa = models.add_player(tid2, "Nguyen Van A", gender="M", actor="t")
pb = models.add_player(tid2, "Tran B", gender="M", actor="t")
pc = models.add_player(tid2, "Le C", gender="M", actor="t")
pw = models.add_player(tid2, "Pham W", gender="F", actor="t")
ms = models.create_event(tid2, "MS", "round_robin", actor="t")
xd = models.create_event(tid2, "XD", "round_robin", actor="t")
e_ms = models.add_entry(ms, pa, actor="t")
models.add_entry(ms, pb, actor="t")
models.add_entry(ms, pc, actor="t")
e_xd = models.add_entry(xd, pa, pw, seed=1, actor="t")
formats.generate_draw(ms, actor="t")
before = {(m2["id"], m2["entry_a_id"], m2["entry_b_id"]) for m2 in models.list_matches(ms)}
models.rename_player(pa, "  Nguyễn  Văn   An ", actor="ref")
check(models.get_player(pa)["name"] == "Nguyễn Văn An", "name saved (spacing tidied)")
check(models.get_entry(e_ms)["name"] == "Nguyễn Văn An", "singles entry shows the new name")
check(models.get_entry(e_xd)["name"] == "Nguyễn Văn An / Pham W", "doubles entry in another event too")
check(models.get_entry(e_xd)["seed"] == 1, "seed untouched")
after = {(m2["id"], m2["entry_a_id"], m2["entry_b_id"]) for m2 in models.list_matches(ms)}
check(before == after, "the draw itself is untouched — same matches, same slots")
try:
    models.rename_player(pb, "le c", actor="ref")
    check(False, "renaming onto another player's name is refused")
except models.RuleError:
    check(True, "renaming onto another player's name is refused")
models.update_player(pc, {"name": "Le Cuong", "gender": "M", "club": "", "rating": None}, actor="t")
check(any(e["name"] == "Le Cuong" for e in models.list_entries(ms)),
      "roster-table edits now update entry names too (they used to go stale)")
models.rename_entry_names(q["entry_a_id"], ["An", "Chau"], actor="ref")
check(models.get_entry(q["entry_a_id"])["name"] == "An / Chau", "quick-match names can be edited")

finish()
