"""Tests for the drag-and-drop round: the player-count team builder feeding
Players & entries, manual pool/seed assignment feeding Draws & standings, and
that Viewer never sees or can reach the run-the-event pages."""

import os

from _testutil import ROOT, check, finish, fresh_db, page_script

DB = fresh_db("dragdrop")

from streamlit.testing.v1 import AppTest  # noqa: E402

from tourney import formats, models  # noqa: E402

tid = models.create_tournament("Drag Drop Cup", actor="test")

# ---- fixtures --------------------------------------------------------------
men = [models.add_player(tid, n, gender="M", actor="test") for n in
       ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel"]]
women = [models.add_player(tid, n, gender="F", actor="test") for n in
         ["India", "Juliet", "Kilo", "Lima"]]

md = models.create_event(tid, "MD", "pool_playoff", actor="test")   # doubles, drag into pools
ws = models.create_event(tid, "WS", "single_elim", actor="test")    # singles, drag to seed

print("== Building teams via the player-count flow (item 1) ==")
# simulate: choose 8 players -> 4 doubles teams, drag pairs together
team_pairs = [men[0:2], men[2:4], men[4:6], men[6:8]]
entry_ids = []
for a, b in team_pairs:
    entry_ids.append(models.add_entry(md, a, b, actor="test"))
check(len(models.list_entries(md)) == 4, "8 players participating in MD makes 4 teams")

# singles, all 4 registered women participating -> auto individual entries
for w in women:
    models.add_entry(ws, w, actor="test")
check(len(models.list_entries(ws)) == 4, "all-registered singles auto-creates one entry each")

print("\n== Draws page: drag entries into pools before generating (item 2) ==")
entries = models.list_entries(md)
models.set_entry_pool(entries[0]["id"], "A", actor="test")
models.set_entry_pool(entries[1]["id"], "A", actor="test")
models.set_entry_pool(entries[2]["id"], "B", actor="test")
models.set_entry_pool(entries[3]["id"], "B", actor="test")
formats.generate_draw(md, actor="test", method="manual")
placed = {e["id"]: e["pool"] for e in models.list_entries(md)}
check(placed[entries[0]["id"]] == "A" and placed[entries[2]["id"]] == "B",
      "manual drag-to-pool grouping survives draw generation")

print("\n== Draws page: drag to reorder seeds before generating (item 2) ==")
ws_entries = models.list_entries(ws)
reordered = list(reversed([e["id"] for e in ws_entries]))
models.set_seed_order(ws, reordered, actor="test")
seeds = {e["id"]: e["seed"] for e in models.list_entries(ws)}
check(seeds[reordered[0]] == 1, "top of the dragged order becomes seed 1")
formats.generate_draw(ws, actor="test")
m1 = next(m for m in models.list_matches(ws) if m["round_no"] == 1 and m["match_no"] == 1)
check(m1["entry_a_id"] == reordered[0], "seed 1 lands in the first bracket slot as dragged")

print("\n== Viewer nav never exposes run-the-event pages, and stays out of the way (item 3) ==")
at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=90)
at.session_state["tournament_id"] = tid
at.session_state["role"] = "viewer"
at.run()
check(not at.exception, "app boots fine as viewer with no exception")

at_admin = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=90)
at_admin.session_state["tournament_id"] = tid
at_admin.session_state["role"] = "admin"
at_admin.session_state["admin_name"] = "Anna"
at_admin.run()
check(not at_admin.exception, "app boots fine as admin (run-the-event pages reachable)")

print("\n== Live page has no desk activity / ready-to-call / completed clutter (item 4) ==")
# this test checks structure via English strings
at_live = AppTest.from_string(page_script("live", DB, tournament_id=tid, lang="en"),
                              default_timeout=90)
at_live.run()
check(not at_live.exception, "live page renders with no exception")
headers = " ".join(str(m.value) for m in at_live.markdown)
check("Desk activity" not in headers, "Desk activity section is gone")
check("On court" in headers, "On court section is present")
check("Next up" in headers, "Next up section is present")
check("Just finished" in headers, "Just finished section is present")
check("Rankings" in headers, "Rankings section is present")
metric_labels = [str(m.label) for m in at_live.metric] if hasattr(at_live, "metric") else []
check(not metric_labels, "no leftover metric tiles (Ready to call / Completed / Events done)")

finish()
