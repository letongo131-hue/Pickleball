"""Fill a database with a realistic demo tournament so every page has
something to show: all five categories, all five formats, a few results in,
one match live on court, and three courts.

    python scripts/seed_demo.py                    # seeds local/demo.db
    python scripts/seed_demo.py --db other.db      # or any SQLite file you name

Refuses to touch a database that already has tournaments in it, so it can't
scribble over real data.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_DEMO_DB = ROOT / "local" / "demo.db"

MEN = ["Nguyen Van A", "Tran Minh B", "Le Quoc C", "Pham Duy D",
       "Hoang Nam E", "Vu Thanh F", "Do Hai G", "Bui Tien H"]
WOMEN = ["Tran Thi I", "Le Ngoc J", "Pham Lan K", "Nguyen Mai L",
         "Dang Thu M", "Vo Ha N", "Ly Kim O", "Cao Anh P"]


def seed(actor: str = "demo") -> int:
    """Seed whatever database `tourney.db` is currently pointed at."""
    from tourney import formats, models

    tid = models.create_tournament("Saigon Open (demo)", venue="Thuan An Sports Centre",
                                   start_date="2026-08-10", actor=actor)
    men = [models.add_player(tid, n, gender="M", club="Riverside", actor=actor) for n in MEN]
    women = [models.add_player(tid, n, gender="F", club="Lakeside", actor=actor) for n in WOMEN]

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
                                  advance_per_pool=2, actor=actor)
        event_ids[cat] = eid
        for i, combo in enumerate(pairs):
            models.add_entry(eid, combo[0], combo[1] if len(combo) > 1 else None,
                             seed=i + 1 if i < 2 else None, actor=actor)
        formats.generate_draw(eid, actor=actor)

    for cat in ("MS", "MD"):
        ready = [m for m in models.list_matches(event_ids[cat]) if models.match_ready(m)]
        for m in ready[:3]:
            fresh = models.get_match(m["id"])
            if fresh["status"] in ("done", "bye"):
                continue
            models.submit_score(m["id"], [(11, 6), (11, 8)], actor="Anna",
                                expected_version=fresh["version"])

    for c in ("Court 1", "Court 2", "Court 3"):
        models.add_court(tid, c, actor=actor)

    live = [m for m in models.list_matches(event_ids["MS"])
            if models.match_ready(m) and m["status"] == "pending"][0]
    models.start_match(live["id"], actor="Ben", court="Court 2")
    models.adjust_point(live["id"], "a", 5, actor="Ben")
    models.adjust_point(live["id"], "b", 3, actor="Ben")
    return tid


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(DEFAULT_DEMO_DB), help="SQLite file to seed")
    args = ap.parse_args()

    os.environ["PICKLEBALL_LOCAL"] = "1"
    from tourney import db, models
    path = db.use_sqlite(args.db)
    if models.list_tournaments(include_quick=True):
        print(f"{path} already has tournaments in it — not seeding over existing data.")
        return 1
    tid = seed()
    print(f"Seeded demo tournament #{tid} into {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
