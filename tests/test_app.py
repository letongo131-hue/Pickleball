"""Boots every page headlessly through Streamlit's AppTest and fails on any
uncaught exception. Also seeds a realistic tournament so the pages have data.

Needs Streamlit installed (pip install -r requirements.txt) but no browser
and no running server."""

import os

from _testutil import ROOT, check, finish, fresh_db, page_script

DB = fresh_db("app")

from streamlit.testing.v1 import AppTest  # noqa: E402

from tourney import formats, models  # noqa: E402

# ---- seed a tournament with all five categories and all five formats -----
tid = models.create_tournament("Saigon Open", venue="Thuan An Sports Centre",
                               start_date="2026-08-10", actor="seed")

MEN = ["Nguyen Van A", "Tran Minh B", "Le Quoc C", "Pham Duy D",
       "Hoang Nam E", "Vu Thanh F", "Do Hai G", "Bui Tien H"]
WOMEN = ["Tran Thi I", "Le Ngoc J", "Pham Lan K", "Nguyen Mai L",
         "Dang Thu M", "Vo Ha N", "Ly Kim O", "Cao Anh P"]

men = [models.add_player(tid, n, gender="M", club="Riverside", actor="seed") for n in MEN]
women = [models.add_player(tid, n, gender="F", club="Lakeside", actor="seed") for n in WOMEN]

plan = [
    ("MS", "round_robin", [(m,) for m in men[:6]]),
    ("WS", "swiss", [(w,) for w in women[:8]]),
    ("MD", "single_elim", [(men[i], men[i + 1]) for i in range(0, 8, 2)]),
    ("WD", "double_elim", [(women[i], women[i + 1]) for i in range(0, 8, 2)]),
    ("XD", "pool_playoff", [(men[i], women[i]) for i in range(8)]),
]
event_ids = {}
for cat, fmt, pairs in plan:
    eid = models.create_event(tid, cat, fmt, swiss_rounds=3, pool_count=2,
                              advance_per_pool=2, actor="seed")
    event_ids[cat] = eid
    for i, combo in enumerate(pairs):
        models.add_entry(eid, combo[0], combo[1] if len(combo) > 1 else None,
                         seed=i + 1 if i < 2 else None, actor="seed")
    formats.generate_draw(eid, actor="seed")

# Play a few matches so pages have live, finished and pending states.
for cat in ("MS", "MD"):
    ms = [m for m in models.list_matches(event_ids[cat]) if models.match_ready(m)]
    for m in ms[:3]:
        fresh = models.get_match(m["id"])
        if fresh["status"] in ("done", "bye"):
            continue
        models.submit_score(m["id"], [(11, 6), (11, 8)], actor="Anna",
                            expected_version=fresh["version"])
live_m = [m for m in models.list_matches(event_ids["MS"]) if models.match_ready(m)
          and m["status"] == "pending"][0]
models.start_match(live_m["id"], actor="Ben", court="Court 2")

for _c in ("Court 1", "Court 2", "Court 3"):
    models.add_court(tid, _c, actor="seed")

print(f"Seeded: 5 events, {len(men) + len(women)} players  ({DB})\n")

PAGE_MODULES = [
    ("Live", "live"),
    ("Draws & standings", "brackets"),
    ("Venue display", "display"),
    ("Courts", "courts"),
    ("Scoring desk", "scoring"),
    ("Quick match", "quick_match"),
    ("Fixtures", "fixtures"),
    ("Players & entries", "players"),
    ("Setup", "setup"),
]


def run_page(module, role="admin", tournament=True):
    script = page_script(module, DB, tournament_id=tid if tournament else None, role=role)
    at = AppTest.from_string(script, default_timeout=90)
    at.run()
    return at


print("== Page renders (signed in as admin) ==")
for title, module in PAGE_MODULES:
    try:
        at = run_page(module)
        errs = [repr(e.value)[:160] for e in at.exception]
        check(not errs, f"{title} renders" + (f" -- {errs[0]}" if errs else ""))
    except Exception as e:
        check(False, f"{title} raised {type(e).__name__}: {e}")

print("\n== Page renders (signed in as referee) ==")
for title, module in PAGE_MODULES:
    try:
        at = run_page(module, role="referee")
        errs = [repr(e.value)[:160] for e in at.exception]
        check(not errs, f"{title} renders for referee" + (f" -- {errs[0]}" if errs else ""))
    except Exception as e:
        check(False, f"{title} raised {type(e).__name__}: {e}")

print("\n== Page renders (public, not signed in) ==")
for title, module in PAGE_MODULES:
    try:
        at = run_page(module, role=None)
        errs = [repr(e.value)[:160] for e in at.exception]
        check(not errs, f"{title} read-only" + (f" -- {errs[0]}" if errs else ""))
    except Exception as e:
        check(False, f"{title} raised {type(e).__name__}: {e}")

print("\n== Pages with no tournament selected ==")
for title, module in PAGE_MODULES:
    try:
        at = run_page(module, tournament=False)
        errs = [repr(e.value)[:160] for e in at.exception]
        check(not errs, f"{title} handles empty state" + (f" -- {errs[0]}" if errs else ""))
    except Exception as e:
        check(False, f"{title} raised {type(e).__name__}: {e}")

print("\n== Referees cannot reach admin-only setup ==")
try:
    at = run_page("setup", role="referee")
    errs = [repr(e.value)[:160] for e in at.exception]
    check(not errs, "setup page does not crash for referee")
    check(any("admin" in str(m.value).lower() for m in at.info),
          "referee is told to sign in as admin, not shown the setup form")
except Exception as e:
    check(False, f"referee setup raised {e}")

print("\n== Full app shell ==")
try:
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=90)
    at.run()
    check(not at.exception, "app.py boots and builds navigation")
    at2 = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=90)
    at2.session_state["tournament_id"] = tid
    at2.session_state["role"] = "admin"
    at2.session_state["admin_name"] = "Anna"
    at2.session_state["ui_lang"] = "en"   # this test checks labels via English strings
    at2.run()
    check(not at2.exception, "app.py boots with a tournament selected")
    picker = [sb for sb in at2.sidebar.selectbox if sb.label == "Tournament"]
    check(picker and any("Saigon Open" in str(o) for o in picker[0].options),
          "sidebar tournament picker offers the seeded tournament")
    check(any("Signed in as" in str(m.value) for m in at2.sidebar.success),
          "sidebar confirms the signed-in admin")
    footer = " ".join(str(c.value) for c in at2.sidebar.caption)
    check("sqlite" in footer and os.path.basename(DB) in footer,
          "sidebar footer shows the app is on the local test database")
except Exception as e:
    check(False, f"app shell raised {e}")

finish()
