"""Targeted tests for this round of changes: gender-eligible entry pools,
the new 'first to 11' scoring preset, and that court changes are now logged
(so every scoring-desk adjustment during a live match is auditable).

Pure engine — no Streamlit needed to run this one."""

from _testutil import check, finish, fresh_db

DB = fresh_db("new_features")

from tourney import db, models  # noqa: E402
from tourney.constants import SCORING_PRESETS  # noqa: E402

tid = models.create_tournament("Feature Test Cup", actor="test")

men = [models.add_player(tid, n, gender="M", actor="test") for n in ["M1", "M2", "M3"]]
women = [models.add_player(tid, n, gender="F", actor="test") for n in ["W1", "W2", "W3"]]
unknown = models.add_player(tid, "Mystery", gender=None, actor="test")

print("== Gender-eligible entry pools (item 4) ==")
md = models.create_event(tid, "MD", "round_robin", actor="test")
players = models.list_players(tid)
pool0 = models.eligible_players("MD", 0, players)
pool1 = models.eligible_players("MD", 1, players)
check(all(p["gender"] == "M" for p in pool0), "MD slot 1 pool is men only")
check(all(p["gender"] == "M" for p in pool1), "MD slot 2 pool is men only")
check(unknown not in pool0, "player with no gender set is excluded from a gendered slot")

xd = models.create_event(tid, "XD", "round_robin", actor="test")
xpool0 = models.eligible_players("XD", 0, players)
xpool1 = models.eligible_players("XD", 1, players)
check(all(p["gender"] == "M" for p in xpool0), "XD slot 1 pool is men")
check(all(p["gender"] == "F" for p in xpool1), "XD slot 2 pool is women")

ms = models.create_event(tid, "MS", "round_robin", actor="test")
check(all(p["gender"] == "M" for p in models.eligible_players("MS", 0, players)),
      "singles category also filters by its required gender")

print("\n== Adding entries only ever records the players actually chosen (item 5) ==")
eid = models.add_entry(md, men[0], men[1], actor="test")
e = models.get_entry(eid)
check({e["player1_id"], e["player2_id"]} == {men[0], men[1]},
      f"MD entry recorded exactly the two chosen players (got {e['player1_id']}, {e['player2_id']})")

print("\n== New scoring preset: 'first to 11' (item 2) ==")
check("11_first" in SCORING_PRESETS, "11_first preset exists")
rule = SCORING_PRESETS["11_first"]
check(models.validate_game(11, 10, rule) is None, "11-10 wins outright under first-to-11")
check(models.validate_game(11, 9, rule) is None, "11-9 wins outright under first-to-11")
check(models.validate_game(10, 9, rule) is not None, "10-9 is not yet a win under first-to-11")
check(models.validate_game(12, 10, rule) is not None,
      "the game cannot run past 11 under first-to-11 (no extension)")

print("\n== Court changes are now logged (item 6: point adjustments are recorded) ==")
event = models.create_event(tid, "WS", "round_robin", actor="test")
e1 = models.add_entry(event, women[0], actor="test")
e2 = models.add_entry(event, women[1], actor="test")
mid = models.create_match(event, "main", 1, 1, entry_a_id=e1, entry_b_id=e2)
before = len(db.query("SELECT id FROM audit_log WHERE entity = 'match' AND entity_id = ?", (mid,)))
models.set_court(mid, "Court 7", actor="Referee Ben")
after = db.query("SELECT * FROM audit_log WHERE entity = 'match' AND entity_id = ? "
                  "ORDER BY id DESC LIMIT 1", (mid,))
check(len(after) == 1 and after[0]["actor"] == "Referee Ben" and after[0]["detail"] == "Court 7",
      "moving a match to a court is attributed and logged")

print("\n== i18n works outside Streamlit ==")
from tourney import i18n  # noqa: E402
i18n.set_lang("en")
check(i18n.t("nav.live") == "Live", "English lookup works with no Streamlit session")
i18n.set_lang("vi")
check(i18n.t("nav.live") == "Trực tiếp", "Vietnamese lookup works with no Streamlit session")
check(models.event_label({"category": "MS"}) == "Đơn nam", "event labels follow the language")

finish()
