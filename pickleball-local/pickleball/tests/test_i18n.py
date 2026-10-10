"""Vietnamese everywhere, format-specific settings, and draw setup living in
Event entries.

1. Static: every tr("...") string in the source has a Vietnamese translation,
   and no tr() call is handed an f-string (which could never be translated).
2. Runtime: every page, as admin / referee / viewer, in every state the seed
   data produces, rendered in Vietnamese — no string falls back to English,
   and no common English UI word is left on screen.
3. Setup shows only the settings of the format that's picked.
4. The draw is set up (method, ordering) in Players & entries → Event
   entries, not on Draws & standings.
"""

import os
import re

os.environ["PICKLEBALL_DEFAULT_LANG"] = "vi"    # before _testutil sets English

from _testutil import ROOT, check, finish, fresh_db, page_script  # noqa: E402

DB = fresh_db("i18n")

from streamlit.testing.v1 import AppTest  # noqa: E402

from tourney import formats, i18n, i18n_catalog, models  # noqa: E402

print("== 1. Every translatable string has Vietnamese ==")
lit, problems = i18n_catalog.literal_calls()
check(not problems, "no tr() call is given an f-string" + (f": {problems}" if problems else ""))
missing = i18n_catalog.missing_vi()
check(not missing, f"all {len(i18n_catalog.all_strings())} strings translated"
      + (f" — missing: {missing[:8]}" if missing else ""))

# --- seed a tournament with every format and some live/finished state -------
tid = models.create_tournament("Giải Sài Gòn Mở rộng", venue="Nhà thi đấu Thuận An",
                               start_date="2026-08-10", actor="seed")
men = [models.add_player(tid, n, gender="M", actor="seed") for n in
       ["Nguyễn Văn An", "Trần Minh Bảo", "Lê Quốc Cường", "Phạm Duy Dũng",
        "Hoàng Nam Em", "Vũ Thành Phát", "Đỗ Hải Giang", "Bùi Tiến Hùng"]]
women = [models.add_player(tid, n, gender="F", actor="seed") for n in
         ["Trần Thị Ích", "Lê Ngọc Ánh", "Phạm Lan Khuê", "Nguyễn Mai Linh",
          "Đặng Thu Mai", "Võ Hà Ngân", "Lý Kim Oanh", "Cao Anh Phương"]]
plan = [("MS", "round_robin", [(m,) for m in men[:6]]),
        ("WS", "swiss", [(w,) for w in women[:8]]),
        ("MD", "single_elim", [(men[i], men[i + 1]) for i in range(0, 8, 2)]),
        ("WD", "double_elim", [(women[i], women[i + 1]) for i in range(0, 8, 2)]),
        ("XD", "pool_playoff", [(men[i], women[i]) for i in range(8)])]
ev = {}
for cat, fmt, pairs in plan:
    ev[cat] = models.create_event(tid, cat, fmt, swiss_rounds=3, actor="seed")
    for i, combo in enumerate(pairs):
        models.add_entry(ev[cat], combo[0], combo[1] if len(combo) > 1 else None, actor="seed")
    formats.generate_draw(ev[cat], actor="seed")
for m in [m for m in models.list_matches(ev["MD"]) if models.match_ready(m)][:2]:
    models.submit_score(m["id"], [(11, 6), (11, 8)], actor="seed",
                        expected_version=models.get_match(m["id"])["version"])
live = [m for m in models.list_matches(ev["MS"]) if m["status"] == "pending"][0]
models.start_match(live["id"], actor="seed", court="Sân 2")
models.record_rally(live["id"], "a", actor="seed")
for c in ("Sân 1", "Sân 2", "Sân 3"):
    models.add_court(tid, c, actor="seed")
# An event with no draw yet, so the draw-setup screens render too.
tid2 = models.create_tournament("Giải Chưa Bốc Thăm", actor="seed")
ms2 = models.create_event(tid2, "MS", "single_elim", actor="seed")
for n in ["Ân", "Bình", "Châu", "Duy"]:
    models.add_entry(ms2, models.add_player(tid2, n, gender="M", actor="seed"), actor="seed")

# Words that only show up when a UI string slipped through untranslated.
ENGLISH = re.compile(
    r"\b(the|and|Add|Save|Delete|Remove|Clear|Confirm|Undo|Switch|Timeout|Sign in|"
    r"match(es)?|entries|entry|player(s)?|event(s)?|Round|Pool|Score|Start|Draw|Generate|"
    r"Pick|Edit|Swap|Court|Seed|Winner|Loser|Champion|Format|Category|Venue|Notes|Status|"
    r"Search|Choose|Select|yet|first|next|live|bracket|standings|Rally|Serve|Game|"
    r"Withdraw|Substitute|Roster|Team|Side|referee|admin)\b")
TAG = re.compile(r"<[^>]+>")


def visible_text(at):
    out = []

    def add(x):
        if x is None:
            return
        x = str(x)
        if x.lstrip().startswith("<style"):
            return
        out.append(TAG.sub(" ", x))

    for kind in ("markdown", "caption", "info", "warning", "success", "error", "title",
                 "header", "subheader"):
        for el in getattr(at, kind, []):
            add(el.value)
    for kind in ("button", "selectbox", "radio", "text_input", "number_input", "checkbox",
                 "toggle", "multiselect", "text_area", "date_input"):
        for el in getattr(at, kind, []):
            add(getattr(el, "label", None))
            add(getattr(el, "placeholder", None))
            for opt in getattr(el, "options", []) or []:
                add(opt)
    for el in getattr(at, "tabs", []):
        add(el.label)
    for el in getattr(at, "expander", []):
        add(el.label)
    for el in getattr(at, "metric", []):
        add(el.label)
    return out


def english_leftovers(texts):
    bad = []
    for t in texts:
        # code chips like `.streamlit/secrets.toml` and the data itself are fine
        t2 = re.sub(r"`[^`]*`", " ", t)
        if ENGLISH.search(t2):
            bad.append(t.strip()[:90])
    return bad


PAGES = ["live", "brackets", "display", "courts", "scoring", "quick_match", "fixtures",
         "players", "setup"]

print("\n== 2. Every page renders fully in Vietnamese ==")
i18n.MISSING.clear()
for role in ("admin", "referee", None):
    for t_id in (tid, tid2):
        for module in PAGES:
            at = AppTest.from_string(page_script(module, DB, tournament_id=t_id, role=role,
                                                 lang="vi"), default_timeout=90)
            at.run()
            who = role or "viewer"
            errs = [repr(e.value)[:120] for e in at.exception]
            if errs:
                check(False, f"{module} ({who}) raised: {errs[0]}")
                continue
            bad = english_leftovers(visible_text(at))
            check(not bad, f"{module} as {who}: no English left on screen"
                  + (f" — e.g. {bad[:3]}" if bad else ""))
check(not i18n.MISSING, "no string fell back to English while rendering"
      + (f": {sorted(i18n.MISSING)[:6]}" if i18n.MISSING else ""))

print("\n== The referee screens, in Vietnamese ==")
script = page_script("scoring", DB, tournament_id=tid, role="referee", lang="vi")
at = AppTest.from_string(script, default_timeout=90)
at.run()
[s for s in at.selectbox if s.label == "Nội dung"][0].set_value(ev["MS"])
at.run()
[b for b in at.button if b.key and "_focusbtn_" in b.key][0].click()
at.run()
texts = visible_text(at)
check(any("thắng pha bóng" in t for t in texts), "rally buttons read '… thắng pha bóng'")
check(any("Hoàn tác" in t for t in texts) and any("Hội ý" in t for t in texts),
      "Undo / Timeout are 'Hoàn tác' / 'Hội ý'")
bad = english_leftovers(texts)
check(not bad, "live referee board has no English" + (f" — {bad[:3]}" if bad else ""))

print("\n== Full app shell in Vietnamese ==")
at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=90)
at.session_state["tournament_id"] = tid
at.run()
side = [str(x.value) for x in at.sidebar.caption] + [str(x.value) for x in at.sidebar.markdown]
check(any("nội dung" in s and "VĐV" in s for s in side), "sidebar summary is in Vietnamese")
check(not at.exception, "app boots in Vietnamese")

print("\n== Round names and errors translate ==")
i18n.set_lang("vi")
check(i18n.round_label("Pool B · Round 2") == "Bảng B · Vòng 2", "pool round name")
check(i18n.round_label("Playoff Semifinal") == "Loại trực tiếp · Bán kết", "playoff round name")
check(i18n.round_label("WB Round of 16") == "Nhánh thắng · Vòng 16 đội", "winners-bracket round")
check(i18n.round_label("LB Round 3") == "Nhánh thua · Vòng 3", "losers-bracket round")
try:
    models.add_court(tid, "   ")
except models.RuleError as e:
    check(str(e) == "Hãy đặt tên cho sân.", "engine errors come out in Vietnamese")

# --------------------------------------------------------------------------
print("\n== 3. Setup shows only the chosen format's settings ==")
os.environ["PICKLEBALL_DEFAULT_LANG"] = "en"
i18n.set_lang("en")     # AppTest formats options in this thread, outside the app session
at = AppTest.from_string(page_script("setup", DB, role="admin", lang="en"), default_timeout=90)
at.run()
fmt_box = [s for s in at.selectbox if s.key == "newt_ev_fmt"][0]


def labels(at):
    return {x.label for x in at.number_input} | {x.label for x in at.checkbox}


expect = {
    "round_robin": set(),
    "single_elim": set(),
    "swiss": {"Swiss rounds"},
    "pool_playoff": {"Pools", "Advance per pool"},
    "double_elim": {"Allow a bracket reset"},
}
format_only = {"Swiss rounds", "Pools", "Advance per pool", "Allow a bracket reset"}
for fmt, want in expect.items():
    fmt_box = [s for s in at.selectbox if s.key == "newt_ev_fmt"][0]
    fmt_box.set_value(fmt)
    at.run()
    shown = labels(at) & format_only
    check(shown == want, f"{fmt}: shows {sorted(want) or 'no extra settings'} (got {sorted(shown)})")

# --------------------------------------------------------------------------
print("\n== 4. Draw setup lives in Event entries ==")
at = AppTest.from_string(page_script("players", DB, tournament_id=tid2, role="admin", lang="en"),
                         default_timeout=90)
at.run()
check(any(r.label == "Draw method" for r in at.radio), "Event entries has the draw method picker")
check(any(b.label == "Generate draw" for b in at.button), "...right next to Generate draw")
at = AppTest.from_string(page_script("brackets", DB, tournament_id=tid2, role="admin", lang="en"),
                         default_timeout=90)
at.run()
check(not any(r.label == "Draw method" for r in at.radio),
      "Draws & standings no longer has its own draw setup")
check(any("Event entries" in str(c.value) for c in at.caption),
      "...it points admins to Event entries instead")

finish()
