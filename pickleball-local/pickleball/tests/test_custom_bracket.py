"""Tests for this round: explicit player selection (no more auto-picking),
the To-15 scoring preset, and the fully custom, hand-wired bracket builder —
including the UI, end to end, reproducing the exact 6-team example from the
request (both winner and loser of one match advancing to different slots)."""

from _testutil import check, finish, fresh_db, page_script

DB = fresh_db("custom_bracket")

from streamlit.testing.v1 import AppTest  # noqa: E402

from tourney import formats, models  # noqa: E402
from tourney.constants import SCORING_PRESETS  # noqa: E402


def admin_page(module, tournament_id):
    at = AppTest.from_string(page_script(module, DB, tournament_id=tournament_id, role="admin"),
                             default_timeout=90)
    at.run()
    return at


tid = models.create_tournament("Custom Bracket Cup", actor="test")

# ---------------------------------------------------------------------------
print("== Item 2: 'To 15' scoring preset exists and validates correctly ==")
check("15_first" in SCORING_PRESETS, "15_first preset is registered")
rule = SCORING_PRESETS["15_first"]
check(models.validate_game(15, 13, rule) is None, "15-13 wins outright")
check(models.validate_game(15, 14, rule) is None, "15-14 wins outright (no win-by-2)")
check(models.validate_game(14, 13, rule) is not None, "14-13 is not yet a win")
check(models.validate_game(16, 14, rule) is not None, "the game cannot run past 15")

# ---------------------------------------------------------------------------
print("\n== Item 1: player selection is explicit, not auto-picked (backend) ==")
ev1 = models.create_event(tid, "MD", "single_elim", actor="test")
roster = [models.add_player(tid, f"Player {i}", gender="M", actor="test") for i in range(1, 13)]
players_all = models.list_players(tid)
pool = models.eligible_players("MD", 0, players_all)
check(len(pool) == 12, "all 12 men are eligible for MD before any selection is made")
# the fix itself is UI-level (multiselect instead of pool[:count]) — verified below via AppTest

# ---------------------------------------------------------------------------
print("\n== Item 1: player-selection UI is a multiselect, not a count ==")
at_e = admin_page("players", tid)
check(not at_e.exception, "players page renders with no exception")
count_inputs = [ni for ni in at_e.number_input if "articipating" in str(ni.label)]
check(not count_inputs, "the old 'how many players' number input is gone")
multiselects = [ms for ms in at_e.multiselect if "articipating" in str(ms.label)]
check(bool(multiselects), "a multiselect for exactly who participates exists instead")
if multiselects:
    ms = multiselects[0]
    # deliberately pick a non-contiguous, non-first-N subset — the old bug
    # would have silently picked the first N eligible players instead.
    chosen = [roster[2], roster[3], roster[8], roster[9]]  # Player 3,4,9,10
    ms.set_value(chosen)
    at_e.run()
    zone_btn = [b for b in at_e.button if b.label == "Create team zones"]
    if zone_btn:
        zone_btn[0].click()
        at_e.run()
    # the tray itself lives inside the sortable drag-and-drop component (an
    # iframe), which isn't inspectable via at.markdown — session_state is
    # the reliable place to check exactly which ids were staged.
    key = f"bld_ids_{ev1}"
    staged = at_e.session_state[key] if key in at_e.session_state else None
    check(staged is not None and sorted(staged) == sorted(chosen),
          "exactly the selected players (3, 4, 9, 10) are staged — not an auto-picked first-N block")

# ---------------------------------------------------------------------------
print("\n== Item 3: custom bracket — the exact 6-team / 3-match example ==")
tid2 = models.create_tournament("Custom Bracket Cup 2", actor="test")
ev2 = models.create_event(tid2, "MD", "single_elim", actor="test", best_of=1, scoring="11_first")
men = [models.add_player(tid2, f"M{i}", gender="M", actor="test") for i in range(1, 13)]
teams = {}
for i, letter in enumerate("ABCDEF"):
    teams[letter] = models.add_entry(ev2, men[i * 2], men[i * 2 + 1], actor="test")

pairs = [(teams["A"], teams["B"]), (teams["C"], teams["D"]), (teams["E"], teams["F"])]
formats.custom_build_round1(ev2, pairs, actor="test")
check(models.get_event(ev2)["draw_method"] == "custom",
      "the event remembers it's using the custom draw method, durably")

r1 = models.list_matches(ev2)
check(len(r1) == 3, "round 1 has exactly the 3 matches the admin paired up")

r2_ids = formats.custom_add_round(ev2, 2, 2, actor="test")
check(len(r2_ids) == 2, "round 2 was created with exactly 2 empty placeholder matches")

m_ab = next(m for m in r1 if m["entry_a_id"] == teams["A"])
m_cd = next(m for m in r1 if m["entry_a_id"] == teams["C"])
m_ef = next(m for m in r1 if m["entry_a_id"] == teams["E"])
r2m1, r2m2 = r2_ids

# exactly the routing from the request: C-vs-D's winner AND loser both
# advance, into two different round-2 matches; A-B and E-F only send winners.
formats.custom_wire(m_ab["id"], winner_to=(r2m1, "A"), loser_to=None, actor="test")
formats.custom_wire(m_cd["id"], winner_to=(r2m1, "B"), loser_to=(r2m2, "A"), actor="test")
formats.custom_wire(m_ef["id"], winner_to=(r2m2, "B"), loser_to=None, actor="test")

for m, winner_side_score in ((m_ab, (11, 5)), (m_cd, (11, 9)), (m_ef, (11, 2))):
    models.start_match(m["id"], actor="test")
    models.submit_score(m["id"], [winner_side_score], actor="test",
                        expected_version=models.get_match(m["id"])["version"])

r2m1_row = models.get_match(r2m1)
r2m2_row = models.get_match(r2m2)
check(r2m1_row["entry_a_id"] == teams["A"] and r2m1_row["entry_b_id"] == teams["C"],
      "round 2 match 1 got the winners of A-vs-B and C-vs-D, as routed")
check(r2m2_row["entry_a_id"] == teams["D"] and r2m2_row["entry_b_id"] == teams["E"],
      "round 2 match 2 got the LOSER of C-vs-D and the winner of E-vs-F — custom routing honored")

# ---------------------------------------------------------------------------
print("\n== Item 3 regression: wiring a match AFTER it's already been played ==")
# The originally-shipped custom_wire only wrote the routing columns — if a
# match had already finished before it was wired (or re-wired), nothing
# ever pushed the winner/loser forward, so the target match stayed stuck on
# TBD forever. This reproduces that exact scenario and confirms the fix.
tid3 = models.create_tournament("Wire-after-finish regression", actor="test")
ev4 = models.create_event(tid3, "MD", "single_elim", actor="test", best_of=1, scoring="11_first")
m4 = [models.add_player(tid3, f"R{i}", gender="M", actor="test") for i in range(1, 13)]
t4 = {}
for i, letter in enumerate("ABCDEF"):
    t4[letter] = models.add_entry(ev4, m4[i * 2], m4[i * 2 + 1], actor="test")
formats.custom_build_round1(
    ev4, [(t4["A"], t4["B"]), (t4["C"], t4["D"]), (t4["E"], t4["F"])], actor="test")
r1_4 = models.list_matches(ev4)
r2_4 = formats.custom_add_round(ev4, 2, 2, actor="test")
m4_ab = next(m for m in r1_4 if m["entry_a_id"] == t4["A"])
m4_cd = next(m for m in r1_4 if m["entry_a_id"] == t4["C"])
m4_ef = next(m for m in r1_4 if m["entry_a_id"] == t4["E"])

# play every round-1 match FIRST, exactly like a live event — routing gets
# decided only afterward, once the admin has seen the results.
for m, score in ((m4_ab, (11, 5)), (m4_cd, (11, 9)), (m4_ef, (11, 2))):
    models.start_match(m["id"], actor="test")
    models.submit_score(m["id"], [score], actor="test",
                        expected_version=models.get_match(m["id"])["version"])
before_a = models.get_match(r2_4[0])["entry_a_id"]
check(before_a is None, "round 2 is still empty right after round 1 finishes, before any wiring")

formats.custom_wire(m4_ab["id"], winner_to=(r2_4[0], "A"), actor="test")
formats.custom_wire(m4_cd["id"], winner_to=(r2_4[0], "B"), loser_to=(r2_4[1], "A"), actor="test")
formats.custom_wire(m4_ef["id"], winner_to=(r2_4[1], "B"), actor="test")

r2_4_m1 = models.get_match(r2_4[0])
r2_4_m2 = models.get_match(r2_4[1])
check(r2_4_m1["entry_a_id"] == t4["A"] and r2_4_m1["entry_b_id"] == t4["C"],
      "wiring after the fact pushes both winners through immediately, not just on the next finish")
check(r2_4_m2["entry_a_id"] == t4["D"] and r2_4_m2["entry_b_id"] == t4["E"],
      "the loser route also pushes through immediately when wired post-hoc")

# re-wiring (changing your mind) should move the entry, not duplicate it
formats.custom_wire(m4_ef["id"], winner_to=(r2_4[0], "B"), actor="test")
check(models.get_match(r2_4[1])["entry_b_id"] is None,
      "re-routing clears the entry out of the old target slot")
check(models.get_match(r2_4[0])["entry_b_id"] == t4["E"],
      "...and places it in the new one, with nothing stale left behind")

print("\n== Item 3: custom builder UI — routing controls for an existing round ==")
# team-building and pool assignment, which (as in test_drag_drop.py) isn't
# something AppTest can simulate dragging within — so round 1 is built via
# the already-verified backend call, and this section exercises the parts
# of the builder that use ordinary widgets: adding a round and routing a
# match, both through the real UI.
ev3 = models.create_event(tid, "WD", "single_elim", actor="test")
women = [models.add_player(tid, f"W{i}", gender="F", actor="test") for i in range(1, 9)]
w_entries = []
for i in range(0, 8, 2):
    w_entries.append(models.add_entry(ev3, women[i], women[i + 1], actor="test"))
formats.custom_build_round1(ev3, [(w_entries[0], w_entries[1]), (w_entries[2], w_entries[3])],
                            actor="test")
check(len(models.list_matches(ev3)) == 2, "round 1 (built via backend) has its 2 matches")

at_d = admin_page("players", tid)   # draw setup now lives in Event entries
check(not at_d.exception, "Event entries renders with an in-progress custom bracket, no exception")
event_picker = [s for s in at_d.selectbox if s.label == "Event"]
if event_picker:
    event_picker[0].set_value(ev3)
    at_d.run()
check(any("Continue building the bracket" in str(e.label) for e in at_d.expander),
      "the builder stays reachable (as an expander) once round 1 already exists")

add_round_input = [ni for ni in at_d.number_input if ni.label == "Round number"]
check(bool(add_round_input) and int(add_round_input[0].value) == 2,
      "the 'add matches to a round' control is present and defaults to round 2")
add_round_btn = [b for b in at_d.button if "round 2" in str(b.label)]
if add_round_btn:
    add_round_btn[0].click()
    at_d.run()
check(len(models.list_matches(ev3)) == 3,
      "round 2 (1 placeholder match, the default count) was created via the real UI")

win_selects = [s for s in at_d.selectbox if s.label == "Winner advances to"]
check(bool(win_selects), "a 'winner advances to' routing control is present for round-1 matches")
r2_match = next(m for m in models.list_matches(ev3) if m["round_no"] == 2)
if win_selects:
    win_selects[0].set_value("R2 · Match 1 · slot A")
    at_d.run()
    save_btns = [b for b in at_d.button if str(b.label) == "Save routing"]
    if save_btns:
        save_btns[0].click()
        at_d.run()
r1_matches = [m for m in models.list_matches(ev3) if m["round_no"] == 1]
routed = any(m["next_match_id"] == r2_match["id"] and m["next_slot"] == "A" for m in r1_matches)
check(routed, "routing a match's winner to a specific round-2 slot via the UI actually saved")

# ---------------------------------------------------------------------------
print("\n== Item 3 regression: topping up an under-provisioned round via the UI ==")
# Originally the "add a round" control only ever offered the *next* round
# number — if you created round 2 with too few matches (e.g. only 1, when
# the bracket needs 2), there was no way back to add a second match to that
# same round; the control would only let you jump straight to round 3.
tid5 = models.create_tournament("Top-up regression", actor="test")
ev5 = models.create_event(tid5, "MD", "single_elim", actor="test")
m5 = [models.add_player(tid5, f"T{i}", gender="M", actor="test") for i in range(1, 13)]
t5 = {}
for i, letter in enumerate("ABCDEF"):
    t5[letter] = models.add_entry(ev5, m5[i * 2], m5[i * 2 + 1], actor="test")
formats.custom_build_round1(
    ev5, [(t5["A"], t5["B"]), (t5["C"], t5["D"]), (t5["E"], t5["F"])], actor="test")
formats.custom_add_round(ev5, 2, 1, actor="test")   # deliberately under-provisioned

at5 = admin_page("players", tid5)
check(not at5.exception, "Event entries renders with an under-provisioned round 2, no exception")

round_input = [ni for ni in at5.number_input if ni.label == "Round number"]
check(bool(round_input) and int(round_input[0].value) == 2,
      "the round-number control defaults to topping up round 2, not jumping to round 3")

add_btn = [b for b in at5.button if "round 2" in str(b.label)]
if add_btn:
    add_btn[0].click()
    at5.run()
r2_now = [m for m in models.list_matches(ev5) if m["round_no"] == 2]
check(len(r2_now) == 2, "a second match was added to the EXISTING round 2 via the real UI")

win_selects5 = [s for s in at5.selectbox if s.label == "Winner advances to"]
check(any("R2 · Match 2 · slot A" in s.options for s in win_selects5),
      "round 1 matches can now be routed to the newly-added round 2 match 2")

# ---------------------------------------------------------------------------
print("\n== Regression: player substitution keeps the entry in its exact draw slot ==")
tid6 = models.create_tournament("Substitution regression", actor="test")
ev6 = models.create_event(tid6, "MD", "round_robin", actor="test")
men6 = [models.add_player(tid6, f"S{i}", gender="M", actor="test") for i in range(6)]
e6a = models.add_entry(ev6, men6[0], men6[1], actor="test")
e6b = models.add_entry(ev6, men6[2], men6[3], actor="test")
formats.generate_draw(ev6, actor="test")
m6 = models.list_matches(ev6)[0]
before_slots = (m6["entry_a_id"], m6["entry_b_id"])

reserve = men6[4]
new_name = models.substitute_player(e6a, men6[1], reserve, actor="test")
check(new_name == models.get_entry(e6a)["name"], "substitute_player returns the updated name")
e6a_row = models.get_entry(e6a)
check(e6a_row["player1_id"] == men6[0] and e6a_row["player2_id"] == reserve,
      "the withdrawn player is replaced and the other half is untouched")
m6_after = models.get_match(m6["id"])
check((m6_after["entry_a_id"], m6_after["entry_b_id"]) == before_slots,
      "the match/bracket slot is completely unchanged by the substitution")

# a player already entered elsewhere can't be subbed in
try:
    models.substitute_player(e6a, men6[0], men6[2], actor="test")
    check(False, "subbing in a player already entered elsewhere should be rejected")
except models.RuleError:
    check(True, "subbing in a player already entered elsewhere is rejected")

# wrong gender for the category is rejected
w6 = models.add_player(tid6, "SW0", gender="F", actor="test")
try:
    models.substitute_player(e6a, men6[0], w6, actor="test")
    check(False, "subbing in the wrong gender should be rejected")
except models.RuleError:
    check(True, "subbing in the wrong gender is rejected")

# ---------------------------------------------------------------------------
print("\n== Regression: 'Manual (drawn outside the app)' actually saves without a drag ==")
# Previously, if the admin never dragged anything (because the default order
# already looked right), nothing was ever written to the database — clicking
# Generate draw failed with a confusing "not recorded" error even though the
# list on screen looked complete. Confirmed fixed via an explicit Record button.
tid7 = models.create_tournament("Manual draw regression", actor="test")
ev7 = models.create_event(tid7, "MS", "single_elim", actor="test")
p7 = [models.add_player(tid7, f"MD{i}", gender="M", actor="test") for i in range(4)]
for pp in p7:
    models.add_entry(ev7, pp, actor="test")
check(all(e["seed"] is None for e in models.list_entries(ev7)),
      "entries start with no seed at all, exactly like a fresh event")

at7 = admin_page("players", tid7)
method_radio7 = [r for r in at7.radio if r.label == "Draw method"]
if method_radio7:
    method_radio7[0].set_value("manual")
    at7.run()
record_btn7 = [b for b in at7.button if "Record this order" in str(b.label)]
check(bool(record_btn7), "the 'Record this order' button is present for Manual mode")
if record_btn7:
    record_btn7[0].click()
    at7.run()
check(all(e["seed"] for e in models.list_entries(ev7)),
      "clicking Record saves every entry's position with zero dragging required")
try:
    formats.generate_draw(ev7, actor="test", method="manual")
    check(True, "generating the manual draw now succeeds")
except models.RuleError as e:
    check(False, f"manual draw generation still fails: {e}")

finish()
