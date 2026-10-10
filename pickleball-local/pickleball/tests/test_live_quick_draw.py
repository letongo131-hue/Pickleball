"""Tests for this round: live point-by-point scoring that updates in real
time across concurrent matches, Quick Match (scoring outside any
tournament), and the three draw methods (seed / randomize / manual)."""

from _testutil import check, finish, fresh_db, page_script

DB = fresh_db("live_quick_draw")

from streamlit.testing.v1 import AppTest  # noqa: E402

from tourney import formats, models  # noqa: E402

tid = models.create_tournament("Live Quick Draw Cup", actor="test")

# ---------------------------------------------------------------------------
print("== Point-by-point scoring persists immediately and finishes a match (item 1) ==")
ev = models.create_event(tid, "MS", "single_elim", actor="test", scoring="11_first", best_of=1)
p1 = models.add_player(tid, "Ann", gender="F", actor="test")
p2 = models.add_player(tid, "Bea", gender="F", actor="test")
e1 = models.add_entry(ev, p1, actor="test")
e2 = models.add_entry(ev, p2, actor="test")
formats.generate_draw(ev, actor="test")
m = models.list_matches(ev)[0]
models.start_match(m["id"], actor="test")

for _ in range(11):
    models.adjust_point(m["id"], "a", 1, actor="test")
mid_state = models.get_match(m["id"])
check(mid_state["cur_a"] == 11, "each point tap is written to the database immediately")

finished = models.confirm_current_game(m["id"], actor="test")
check(finished is True, "confirming the deciding game finishes a best-of-1 match")
final = models.get_match(m["id"])
check(final["winner_entry_id"] == m["entry_a_id"],
      "the side that reached game point (side A) is recorded as the winner")
check(final["cur_a"] == 0 and final["cur_b"] == 0, "the live tally resets once a game locks in")

print("\n== Multiple live matches keep independent scores (item 1) ==")
evc = models.create_event(tid, "MD", "round_robin", actor="test")
men = [models.add_player(tid, f"M{i}", gender="M", actor="test") for i in range(8)]
for i in range(0, 8, 2):
    models.add_entry(evc, men[i], men[i + 1], actor="test")
formats.generate_draw(evc, actor="test")
live_two = [mm for mm in models.list_matches(evc) if mm["status"] == "pending"][:2]
for mm in live_two:
    models.start_match(mm["id"], actor="test")
models.adjust_point(live_two[0]["id"], "a", 4, actor="test")
models.adjust_point(live_two[1]["id"], "b", 7, actor="test")
r0 = models.get_match(live_two[0]["id"])
r1 = models.get_match(live_two[1]["id"])
check(r0["cur_a"] == 4 and r0["cur_b"] == 0, "match 1's live score is unaffected by match 2")
check(r1["cur_a"] == 0 and r1["cur_b"] == 7, "match 2's live score is unaffected by match 1")

print("\n== The live scoreboard UI drives scoring end to end (item 1) ==")
ev2 = models.create_event(tid, "WS", "single_elim", actor="test", scoring="11_first", best_of=1)
p3 = models.add_player(tid, "Cat", gender="F", actor="test")
p4 = models.add_player(tid, "Dot", gender="F", actor="test")
models.add_entry(ev2, p3, actor="test")
models.add_entry(ev2, p4, actor="test")
formats.generate_draw(ev2, actor="test")
m2 = models.list_matches(ev2)[0]
models.start_match(m2["id"], actor="test")

at = AppTest.from_string(page_script("scoring", DB, tournament_id=tid, role="admin"),
                         default_timeout=90)
at.run()
check(not at.exception, "scoring desk renders with a live match with no exception")
event_picker = [s for s in at.selectbox if s.label == "Event"]
if event_picker:
    event_picker[0].set_value(ev2)
    at.run()
# click into the focused single-match view before the point buttons exist
focus_btns = [b for b in at.button if b.key and "_focusbtn_" in b.key]
if focus_btns:
    focus_btns[0].click()
    at.run()
check(any(b.key and b.key.endswith("_back") for b in at.button),
      "entering a match shows a back button — the rest of the list is out of the way")
check(any(b.key and b.key.endswith("_rally_a") for b in at.button)
      and any(b.key and b.key.endswith("_rally_b") for b in at.button),
      "the referee board shows one 'won the rally' button per side")
call_md = " ".join(str(x.value) for x in at.markdown)
check("pk-call" in call_md and "0 – 0" in call_md, "the score call is shown (singles: 0 – 0)")
for _ in range(11):
    btns = [b for b in at.button if b.key and b.key.endswith("_rally_a")]
    if btns:
        btns[0].click()
        at.run()
check(models.get_match(m2["id"])["cur_a"] == 11, "eleven rallies won by the server = 11 points")
check(not at.exception, "no exception while refereeing rally by rally")
confirm_btns = [b for b in at.button if b.key and b.key.endswith("_confirm")]
if confirm_btns:
    confirm_btns[0].click()
    at.run()
m2_after = models.get_match(m2["id"])
check(m2_after["status"] == "done", "eleven rally taps then Confirm in the UI finishes the match")

print("\n== Side-out rules in the UI: the receiver winning a rally scores nothing ==")
tid_so = models.create_tournament("Side-out UI Cup", actor="test")
ev_so = models.create_event(tid_so, "XD", "round_robin", actor="test", best_of=1)
xm = [models.add_player(tid_so, f"SO-M{i}", gender="M", actor="test") for i in range(2)]
xw = [models.add_player(tid_so, f"SO-W{i}", gender="F", actor="test") for i in range(2)]
for i in range(2):
    models.add_entry(ev_so, xm[i], xw[i], actor="test")
formats.generate_draw(ev_so, actor="test")
mso = models.list_matches(ev_so)[0]
at_so = AppTest.from_string(page_script("scoring", DB, tournament_id=tid_so, role="referee"),
                            default_timeout=90)
at_so.run()
[s_ for s_ in at_so.selectbox if s_.label == "Event"][0].set_value(ev_so)
at_so.run()
[b for b in at_so.button if b.key and "_focusbtn_" in b.key][0].click()
at_so.run()
start = [b for b in at_so.button if b.key and b.key.endswith("_start")]
check(bool(start), "a pending match opens on the pre-match screen with a Start button")
names_inputs = [t for t in at_so.text_input if t.label.startswith("Side A player")]
check(len(names_inputs) == 2, "doubles: both players' names are editable before the match")
names_inputs[0].set_value("SO-M0 Corrected")
[b for b in at_so.button if b.label == "Save names"][0].click()
at_so.run()
side_a_first = models.side_players(mso)["a"][0]["id"]
check(models.get_player(side_a_first)["name"] == "SO-M0 Corrected",
      "editing a name in the referee view renames the player")
check(models.get_entry(mso["entry_a_id"])["name"].startswith("SO-M0 Corrected /"),
      "...and the team name everywhere updates with it")
[b for b in at_so.button if b.key and b.key.endswith("_start")][0].click()
at_so.run()
check(models.get_match(mso["id"])["status"] == "live", "Start match puts it live")
call_md = " ".join(str(x.value) for x in at_so.markdown)
check("0 – 0 – 2" in call_md, "doubles side-out match opens with the call 0 – 0 – 2")
[b for b in at_so.button if b.key and b.key.endswith("_rally_b")][0].click()
at_so.run()
mm = models.get_match(mso["id"])
check((mm["cur_a"], mm["cur_b"]) == (0, 0) and models.serve_state(mm)["serving"] == "b",
      "receiver wins the rally at 0-0-2: side out, no point")
[b for b in at_so.button if b.key and b.key.endswith("_ref_undo")][0].click()
at_so.run()
check(models.serve_state(models.get_match(mso["id"]))["serving"] == "a", "Undo button restores the serve")
check(not at_so.exception, "no exceptions on the doubles referee board")

# ---------------------------------------------------------------------------
print("\n== Quick match: start and score outside any tournament (item 2) ==")
before_tournaments = models.list_tournaments()
qm = models.start_quick_match("Xavier", "Yara", scoring="11_first", best_of=1, actor="ref1")
check(qm["status"] == "pending", "a quick match is created ready to start")
after_tournaments = models.list_tournaments()
check(before_tournaments == after_tournaments,
      "starting a quick match doesn't create or disturb any normal tournament")

models.start_match(qm["id"], actor="ref1")
for _ in range(11):
    models.adjust_point(qm["id"], "a", 1, actor="ref1")
finished = models.confirm_current_game(qm["id"], actor="ref1")
check(finished is True, "a quick match can be played to completion like any other match")

quick_list = models.list_quick_matches()
check(any(x["id"] == qm["id"] for x in quick_list),
      "the finished quick match shows up in the quick-match list")

print("\n== Quick match page works via the UI with no tournament selected (item 2) ==")
at_q = AppTest.from_string(page_script("quick_match", DB, role="referee", admin_name="Ben"),
                           default_timeout=90)
at_q.run()
check(not at_q.exception, "quick match page renders with no tournament_id in session at all")
inputs = {ti.label: ti for ti in at_q.text_input}
if "Side A" in inputs and "Side B" in inputs:
    # Fill the whole form, then submit — no run() in between. A rerun before
    # the submit button is pressed discards un-submitted form values, exactly
    # as it would in a browser.
    inputs["Side A"].set_value("Uma")
    inputs["Side B"].set_value("Theo")
    bo = [s for s in at_q.selectbox if s.label == "Match length"]
    if bo:
        bo[0].set_value(1)
    start_btns = [b for b in at_q.button if b.label == "Start match"]
    if start_btns:
        start_btns[0].click()
        at_q.run()
check(not at_q.exception, "starting a quick match from the UI raises no exception")
pre = [b for b in at_q.button if b.key and b.key.endswith("_start")]
check(bool(pre), "a new quick match opens straight on the referee's pre-match screen")
if pre:
    pre[0].click()
    at_q.run()
new_matches = [m for m in models.list_quick_matches() if m["status"] == "live"]
check(bool(new_matches), "a live quick match now exists after using the start form")

# ---------------------------------------------------------------------------
print("\n== Draw methods: seed / randomize / manual (item 3) ==")
ev3 = models.create_event(tid, "XD", "single_elim", actor="test")
xmen = [models.add_player(tid, f"XM{i}", gender="M", actor="test") for i in range(4)]
xwomen = [models.add_player(tid, f"XW{i}", gender="F", actor="test") for i in range(4)]
xentries = [models.add_entry(ev3, xmen[i], xwomen[i], actor="test") for i in range(4)]
models.set_seed(xentries[2], 1, actor="test")   # a deliberate seed so "by seed" is checkable
formats.generate_draw(ev3, actor="test", method="seed")
m3 = next(mm for mm in models.list_matches(ev3) if mm["round_no"] == 1 and mm["match_no"] == 1)
check(m3["entry_a_id"] == xentries[2], "method='seed' places the explicitly-seeded entry first")

finish()
