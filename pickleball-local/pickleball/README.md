# Pickleball Tournament Desk

A scoring and ranking app for pickleball tournaments. Python + Streamlit, built to run
in VSCode and deploy from GitHub to Streamlit Community Cloud.

Run several tournaments, all five categories in each, a different format per category,
with a live scoreboard the crowd can watch and a desk several admins can share.

---

## Quick start: run and test on your own machine

Nothing below talks to Streamlit Cloud or your hosted database. Works the same on
Windows, macOS and Linux.

```bash
python -m venv .venv
.venv\Scripts\activate             # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt

python run_tests.py                # all 10 test files, ~40 seconds
python run_local.py                # opens the app on a demo tournament
```

| Command | What it does |
|---|---|
| `python run_tests.py` | Every test, each in its own process on its own throwaway database |
| `python run_tests.py --engine` | Engine tests only — about a second, no Streamlit needed |
| `python run_tests.py schedule` | Only tests whose name contains "schedule" |
| `pytest` | Same suite through pytest (VSCode's Testing panel picks this up) |
| `python tests/test_engine.py` | One test file on its own, full output |
| `python run_local.py` | App at http://localhost:8501 on `local/demo.db`, seeded on first run |
| `python run_local.py --reset` | Wipe and re-seed the demo database |
| `python run_local.py --empty` | Start from an empty `local/scratch.db` |
| `python run_local.py --copy-of backup.db` | Work on a *copy* of any SQLite file; the original is never opened |

Sign in locally with admin passcode `pickle`, referee `referee` (unless your
`secrets.toml` sets others). The sidebar footer always shows which database is in use.

In VSCode, `.vscode/launch.json` has ready-made F5 entries: run locally (demo or
empty), run all tests, engine tests only, and **debug the open test file** with
breakpoints.

### Why local runs can't touch the live data

`tourney/db.py` picks the database in this order:

1. `PICKLEBALL_DB=/some/file.db` → that SQLite file, always.
2. `PICKLEBALL_LOCAL=1` → the default local SQLite file.
3. `DATABASE_URL` env var → Postgres.
4. `[database].url` in `.streamlit/secrets.toml` → Postgres.
5. otherwise `pickleball.db` next to `app.py`.

The tests and `run_local.py` always set 1 or 2, so even with your production Postgres
URL sitting in `secrets.toml`, they stay on local SQLite. The deployed app on Streamlit
Cloud sets neither, so it keeps using the Postgres URL from secrets exactly as before.

Test databases live in your temp folder (`%TEMP%\pickleball-tests` on Windows), and
`local/` holds your local app databases — both are git-ignored.

---

## Language (Tiếng Việt / English)

The app opens in **Vietnamese**; switch with **Ngôn ngữ / Language** in the sidebar.
Every screen, button, message, round name ("Bán kết", "Bảng A · Vòng 2") and error from
the engine is translated.

For developers: write user-facing text in English inside `tr("…")`, with `{placeholders}`
instead of f-strings — `tr("{n} entries", n=len(entries))` — and add the Vietnamese to
`tourney/vi.py`. `python -m tourney.i18n_catalog` lists anything untranslated, and
`tests/test_i18n.py` fails the build if a string is missing or English is left on any page.

## Where the draw is set up

Everything about an event's draw is in **Players & entries → Event entries**, under the
entry list: the draw method (by seed / random / manual / custom), dragging entries into
order or into pools, the format's options, **Generate draw**, the custom bracket builder
and **Clear draw**. **Draws & standings** only shows the results.

---

## Refereeing on a tablet

Open **Scoring desk** (or **Quick match**), tap **Score →** on a match.

**Before the match** — the pre-match screen lets the referee check and correct player
names, set the court, pick who serves first, and (doubles) who starts in the right
court. Then **▶ Start match**.

**During the match** the referee only answers one question per rally: *who won it?*

- The **score call** in big type — `4 – 2 – 1` in side-out doubles — ready to read aloud.
- The **court as the referee sees it**: both sides on their current ends, every player in
  the court they're standing in, the server lit up with a ball and the court they serve
  from.
- Two **"won the rally" buttons**, each under its own side of the court. They follow the
  players when ends change, so the left button is always the side on the left.
- **Undo** (steps back exactly one rally, timeout or setup change), **timeouts** per side
  with the allowance shown, and **Switch ends**.
- **Game point / match point** badges, a **Switch ends now!** prompt at the right score in
  the deciding game, and **Confirm game** when a game is won (then the next game is set up:
  ends change, the side that received first serves first).
- **Tablet full-screen** (on by default) hides the menu; **← All matches** gets you back.
- Expanders for **Edit player names**, **Correct the score by hand**, and **Retire a side /
  type the whole score**.

### Scoring rules built in (`tourney/rules.py`)

| | Side-out scoring (default) | Rally scoring |
|---|---|---|
| Who scores | Only the serving side | Whoever wins the rally |
| Doubles servers | Server 1 then server 2, then side out | One server, then side out |
| Start of game | `0-0-2` — first serving side gets one server | Normal |
| Serving side wins | Point; server switches courts with partner | Same |
| Receivers win | Server 2 (from where partner stands) or side out | Point + serve; player in the court matching their score serves |
| Singles | Serve from right on even score, left on odd | Same |
| Call | `server – receiver – server#` | `server – receiver` |

Plus: game ends at the target with the required lead or at the cap; ends switch at 6 / 8 /
11 (games to 11 / 15 / 21) in the deciding game and between games; 2 timeouts per game
(3 in games to 21); a position check that warns if players' courts don't match their score.
Choose the system per event on **Setup**, or per Quick match.

### Correcting a name right before (or during) a match

**Edit player names** in the referee view renames the registered player *everywhere*:
every event they're entered in, draws, standings, the Live board and Venue display.
Seeds, draw positions and results don't move. Quick-match names can be edited the same
way. (Name edits on the **Players & entries → Roster** table now propagate the same way;
before, they left the old name on the player's entries.)

---

## What it does

| Feature | Where it lives |
|---|---|
| Multiple tournaments, switch between them | Sidebar picker; **Setup** page to create |
| All 5 categories in one tournament | **Setup** → Add an event (MS, WS, MD, WD, XD) |
| 5 formats, chosen per category | Swiss, Round Robin, Single Elim, Double Elim, Pool → Playoffs |
| Live dashboard, standings, brackets | **Live** (auto-refreshes) and **Draws & standings** |
| Live vs finished matches | **Live** board and **Scoring desk** → Open / Finished tabs |
| Several people entering scores at once | Named sign-in, per-match version check, soft claims, audit log |
| Three access levels: Admin, Referee, Viewer | See **Roles** below |
| Change fixtures with repeat-matchup detection | **Fixtures** page |
| Court assignment that won't double-book a player | **Courts** page |
| Full-screen board for a TV at the venue | **Venue display** page |
| Build the draw right where you enter it | **Players & entries** → Event entries |

### Formats in detail

- **Round Robin** — everyone plays everyone once, built by the circle method. Odd entry
  counts give a rotating bye.
- **Swiss** — you pair one round at a time from the current standings. Pairing backtracks
  to avoid rematches, and the bye goes to the lowest-ranked entry who has not had one.
  Ties break on Buchholz (the combined wins of the opponents you actually faced).
- **Single Elimination** — seeded bracket padded to a power of two, byes resolved
  automatically, optional 3rd place match.
- **Double Elimination** — winners bracket, losers bracket, grand final. Losers drop into
  the losers side with the drop order reversed on alternate rounds so you are less likely
  to immediately replay whoever beat you. If the losers-bracket survivor wins the grand
  final, both sides have one loss, so a deciding "bracket reset" match is created.
- **Pool Play → Playoffs** — seeds are snaked across pools so each pool gets a comparable
  spread. Every pool plays a round robin; once they all finish, the top *n* from each pool
  are seeded into a knockout bracket.

### Courts and calling matches on

A player entered in Men's Singles *and* Mixed Doubles is one human being, but the two
draws know nothing about each other. The **Courts** page works at the player level
across every event:

- **Call next** looks at every ready match in the whole tournament, skips anyone already
  on court in another category, and fills the free courts. It will leave a court idle
  rather than double-book someone.
- **Assign manually** places a specific match on a specific court and tells you the clash
  before you commit. You can override knowingly.
- **Player load** lists everyone with matches outstanding, busiest first.

The **Venue display** page is a read-only board for a TV by the courts. Collapse the
sidebar and press F11.

### Ranking

Ties break in this order: match win %, then head-to-head among only the tied entries,
then game differential, then point differential, then points scored, then Buchholz.

---

## Roles

| Role | Can do |
|---|---|
| **Admin** | Everything — tournaments, events, players, entries, draws, courts, fixtures, scoring. |
| **Referee** | The **Scoring desk** and **Quick match** only. Every save is stamped and logged. |
| **Viewer** | No sign-in needed. Read-only: Live, Draws & standings, Venue display. |

Passcodes live in `.streamlit/secrets.toml` (copy `secrets.toml.example`):

```toml
[admin]
passcode = "change-me, second-admin-code"

[referee]
passcode = "change-me-too, second-referee-code"
```

Defaults if unset: admin `pickle`, referee `referee` — change both before a real event.

---

## Backup: run everyone off one laptop at the venue

```bash
python run_local.py --venue
```

It prints the address tablets and screens on the same Wi-Fi should open
(e.g. `http://192.168.1.23:8501`). Data is kept in `local/venue.db` and is
never mixed with the online database, even if `DATABASE_URL` or a secrets
URL is set. If tablets can't connect, allow Python through the laptop's firewall.

---

## Deploy online: Render (Singapore) + Neon Postgres (Singapore), free

1. **Neon** (https://neon.tech): new project, region **AWS Asia Pacific
   (Singapore)**. Click **Connect**, turn **Connection pooling off**, copy the
   connection string (`postgresql://…?sslmode=require`).
2. Push this folder to a GitHub repo (`render.yaml` must be at the top level).
3. **Render** (https://render.com): **New → Blueprint**, pick the repo. Fill in
   `DATABASE_URL` (the Neon string), `PICKLEBALL_ADMIN_PASSCODE` and
   `PICKLEBALL_REFEREE_PASSCODE` (comma-separate several codes). Deploy.
4. Open `https://<name>.onrender.com`. The sidebar footer should say
   `postgres · …neon.tech`.

The free web service sleeps after 15 minutes without visitors; the first visit
then takes about a minute. Open the app a few minutes before play starts.

Streamlit Community Cloud also still works (secrets: `[admin]`, `[referee]`,
`[database] url = "postgresql://…"`), but it runs only in the US, which makes
every click several times slower from Vietnam.

---

## How several admins share one desk

- Each admin signs in with their own name; every save is stamped and logged.
- Each match carries a version number. If two admins save the same match, the second
  save is **rejected** and names who got there first.
- Opening a match places a soft five-minute claim so others see who's scoring it.
- Adding the same player name twice is merged rather than duplicated.
- SQLite runs in WAL mode with short transactions, so the live board never blocks.

## Fixture editing and repeat matchups

The **Fixtures** page refuses to save a pairing that already meets elsewhere in the event
unless you tick **Allow a rematch anyway**. A **Repeat check** tab lists every pair
scheduled more than once.

## Correcting mistakes

Finished matches can be reopened from **Scoring desk → Finished → Correct this result**,
as long as the next match they feed hasn't started.

---

## Project layout

```
app.py                  entry point, sign-in, navigation
run_local.py            start the app on a throwaway local database
run_tests.py            run the whole test suite (any OS)
pytest.ini              lets `pytest` / VSCode run the same suite
scripts/seed_demo.py    demo tournament seeder
tourney/                the engine — importable and testable without Streamlit
  constants.py          categories, formats, scoring presets
  db.py                 SQLite / Postgres layer, schema, audit log, DB selection
  models.py             CRUD, score validation, result propagation, fixture guards
  formats.py            the five draw builders + custom brackets
  standings.py          rankings, tiebreakers, final placings
  schedule.py           court assignment, cross-event player conflicts
  i18n.py               English / Vietnamese strings
  rules.py              pickleball scoring rules (pure functions, no database)
  vi.py                 Vietnamese translations for every tr() string
  i18n_catalog.py       finds every translatable string (used by the tests)
views/                  Streamlit pages
  referee.py            the tablet referee board
tests/
  _testutil.py          per-test temp database, check/finish helpers
  pytest_suite.py       pytest bridge
  test_engine.py        whole tournaments in every format          (engine)
  test_schedule.py      cross-event court conflicts                (engine)
  test_new_features.py  gender pools, scoring presets, audit, i18n (engine)
  test_rules.py         every scoring rule, rally undo, renames      (engine)
  test_app.py           every page renders in every auth state     (UI)
  test_themes.py        theme CSS and picker                       (UI)
  test_live_quick_draw.py  point-by-point scoring, quick match     (UI)
  test_drag_drop.py     pools, seeding, viewer nav                 (UI)
  test_custom_bracket.py   hand-wired brackets, substitutions      (UI)
  test_i18n.py          Vietnamese on every page; setup & draw layout (UI)
```

UI tests drive the real pages through `streamlit.testing.v1.AppTest` — headless, no
browser and no server needed.

## Scoring rules supported

To 11 (first-to or win by 2, optional cap 15), to 15 (first-to, win by 2, or cap 21),
to 21 win by 2. Best of 1, 3, or 5, set per event. Retirements are recorded as a win for
the opponent with the games played so far kept on record. The desk cannot save an
impossible score.
