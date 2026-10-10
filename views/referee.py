"""Tablet referee view — what the referee holds courtside.

One question per rally: who won it? Everything else (point or side out,
server 1 or 2, who serves from which court, when to switch ends, game over)
comes from `tourney.rules`. Laid out for a tablet held in landscape:

  * the court as the referee sees it, both sides on the ends they're on now,
    with the server and the court they serve from lit up;
  * the full score call ("4 – 2 – 1") in big type, to read out loud;
  * two huge "won the rally" buttons, each under its own side of the court —
    they swap sides when the players change ends, so the left button is
    always the side on the left;
  * Undo, timeouts and switch-ends as large secondary buttons;
  * name corrections, serve setup and hand corrections tucked into expanders.

All actions run as button callbacks, so a tap costs one rerun, not two.
"""

from __future__ import annotations

import html
import zlib

import streamlit as st

from tourney import i18n, models, rules
from tourney.i18n import tr
from views import ui

TEAM_COLOR = {"a": "#1565C0", "b": "#C2410C"}     # fixed, readable on every theme

REF_CSS = """
<style>
button { touch-action: manipulation; }
.pk-ref-meta { display:flex; flex-wrap:wrap; gap:.4rem .9rem; align-items:center;
  font-size:.82rem; letter-spacing:.06em; text-transform:uppercase; color:var(--mute);
  font-weight:700; margin:.1rem 0 .5rem; }
.pk-ref-meta .chip { background: var(--panel2); border:1px solid var(--line); border-radius:999px;
  padding:.15rem .6rem; color: var(--ink); }
.pk-call { font-family: var(--font-display); font-weight: 900; text-align:center; color: var(--ink);
  font-size: clamp(2.2rem, 6vw, 3.9rem); line-height: 1; margin: 0 0 .1rem;
  font-variant-numeric: tabular-nums; letter-spacing: .02em; }
.pk-callsub { text-align:center; color: var(--ink); font-size: clamp(1rem, 2vw, 1.2rem); margin-bottom:.35rem; }
.pk-ref-title { font-weight:800; color: var(--ink); font-size: 1.05rem; margin: 0; }
.pk-callsub b { color: var(--rust); }
.pk-badges { display:flex; justify-content:center; gap:.5rem; flex-wrap:wrap; margin-bottom:.4rem; }
.pk-badges:empty { display:none; }
.pk-badge { border-radius: 999px; padding: .25rem .8rem; font-weight: 800; letter-spacing: .08em;
  font-size: .85rem; text-transform: uppercase; color:#fff; }
.pk-badge.gp { background:#d93025; } .pk-badge.mp { background:#7b1fa2; }
.pk-badge.sw { background:#e3a008; color:#1b1b1b; } .pk-badge.go { background:#1e9e55; }
.pk-badge.warn { background:#b45309; }

.pk-ct { display:grid; grid-template-columns: 1fr 8px 1fr; border: 3px solid var(--ink);
  border-radius: 12px; overflow: hidden; background: var(--parchment); }
.pk-net { background: repeating-linear-gradient(180deg, var(--ink) 0 7px, transparent 7px 12px); }
.pk-half { display:grid; grid-template-rows: auto 1fr 1fr; }
.pk-half.L { grid-template-columns: 1fr 22%; grid-template-areas: "head head" "top kit" "bot kit"; }
.pk-half.R { grid-template-columns: 22% 1fr; grid-template-areas: "head head" "kit top" "kit bot"; }
.pk-hh { grid-area: head; display:flex; align-items:center; justify-content:space-between; gap:.6rem;
  padding:.3rem .8rem; color:#fff; }
.pk-hh .tn { font-weight: 800; font-size: clamp(.95rem, 1.8vw, 1.15rem); overflow:hidden;
  text-overflow: ellipsis; white-space: nowrap; }
.pk-hh .to { font-size:.75rem; opacity:.9; white-space:nowrap; }
.pk-hh .sc { font-family: var(--font-display); font-weight: 900; font-size: clamp(1.8rem, 4.5vw, 2.8rem);
  line-height: 1; font-variant-numeric: tabular-nums; }
.pk-kit { grid-area: kit; display:flex; align-items:center; justify-content:center;
  writing-mode: vertical-rl; font-size: .66rem; letter-spacing: .3em; color: var(--mute);
  background: color-mix(in srgb, var(--ink) 6%, transparent); }
.pk-half.L .pk-kit { border-left: 2px solid var(--ink); }
.pk-half.R .pk-kit { border-right: 2px solid var(--ink); }
.pk-box { min-height: clamp(62px, 11vh, 120px); padding: .4rem .8rem; display:flex; flex-direction:column;
  justify-content:center; gap:.15rem; }
.pk-box.top { grid-area: top; border-bottom: 2px solid var(--ink); }
.pk-box.bot { grid-area: bot; }
.pk-pname { font-weight: 800; font-size: clamp(1.05rem, 2.3vw, 1.55rem); color: var(--ink); line-height:1.2; }
.pk-ctag { font-size:.7rem; letter-spacing:.14em; text-transform: uppercase; color: var(--mute); }
.pk-box.srv { background: color-mix(in srgb, #d7f23a 38%, var(--parchment));
  box-shadow: inset 0 0 0 3px #9bb31c; }
.pk-ball { display:inline-block; width:.85em; height:.85em; border-radius:50%; background:#d7f23a;
  border:2px solid #7d9416; vertical-align: -0.05em; margin-right:.35rem; }
.pk-flash { border-radius: 10px; padding:.55rem .9rem; margin-bottom:.5rem; font-weight:700;
  font-size: 1.05rem; text-align:center; }
.pk-flash.info { background: color-mix(in srgb, #2b7bd6 16%, var(--parchment)); color: var(--ink); }
.pk-flash.error { background: color-mix(in srgb, #d93025 18%, var(--parchment)); color: var(--ink); }
.pk-flash.big { background: #e3a008; color: #1b1b1b; font-size: 1.3rem; }

/* the two rally buttons — sized for thumbs, coloured per side */
div[class*="st-key-"][class*="_rally_"] button {
  min-height: clamp(96px, 17vh, 210px); border-radius: 18px !important; border: none !important;
  text-transform: none !important; color: #fff !important; box-shadow: 0 4px 14px rgba(0,0,0,.18); }
div[class*="st-key-"][class*="_rally_"] button p { font-size: clamp(1.25rem, 3vw, 2rem) !important;
  font-weight: 800 !important; line-height: 1.25; color:#fff !important; }
div[class*="st-key-"][class*="_rally_a"] button { background: #1565C0 !important; }
div[class*="st-key-"][class*="_rally_b"] button { background: #C2410C !important; }
div[class*="st-key-"][class*="_rally_"] button div, div[class*="st-key-"][class*="_rally_"] button p {
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }
div[class*="st-key-"][class*="_ref_to_a"] button { border: 2px solid #1565C0 !important; }
div[class*="st-key-"][class*="_ref_to_b"] button { border: 2px solid #C2410C !important; }
div[class*="st-key-"][class*="_ref_to_a"] button p { color: #1565C0 !important; font-weight: 800 !important; }
div[class*="st-key-"][class*="_ref_to_b"] button p { color: #C2410C !important; font-weight: 800 !important; }
div[class*="st-key-"][class*="_rally_"] button:active { transform: scale(.98); filter: brightness(.92); }
div[class*="st-key-"][class*="_rally_"] button:disabled { opacity: .35; }
div[class*="st-key-"][class*="_ref_"] button, div[class*="st-key-"][class*="_back"] button {
  min-height: 62px; }
div[class*="st-key-"][class*="_ref_"] button p { font-size: 1.05rem !important; }
div[class*="st-key-"][class*="_confirm"] button, div[class*="st-key-"][class*="_start"] button,
div[class*="st-key-"][class*="_startbtn"] button {
  min-height: 84px; border-radius: 14px !important; }
div[class*="st-key-"][class*="_confirm"] button p, div[class*="st-key-"][class*="_start"] button p {
  font-size: 1.35rem !important; font-weight: 800 !important; }
@media (max-width: 760px) { .pk-kit { display:none; }
  .pk-half.L { grid-template-columns: 1fr; grid-template-areas: "head" "top" "bot"; }
  .pk-half.R { grid-template-columns: 1fr; grid-template-areas: "head" "top" "bot"; } }
</style>
"""

FULLSCREEN_CSS = """
<style>
section[data-testid="stSidebar"], div[data-testid="stSidebarCollapsedControl"],
header[data-testid="stHeader"], .pk-head { display: none !important; }
div[data-testid="stMainBlockContainer"] div[data-testid="stVerticalBlock"] { gap: .55rem; }
div[data-testid="stMainBlockContainer"], .block-container {
  padding-top: .8rem !important; padding-left: 1rem !important; padding-right: 1rem !important;
  padding-bottom: 2rem !important; max-width: 100% !important; }
</style>
"""


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _esc(s) -> str:
    return html.escape(str(s))


def _flash(kind: str, msg: str):
    st.session_state["ref_flash"] = (kind, msg)


def _show_flash():
    f = st.session_state.pop("ref_flash", None)
    if f:
        kind, msg = f
        st.markdown(f'<div class="pk-flash {kind}">{_esc(msg)}</div>', unsafe_allow_html=True)


def team_names(m, emap) -> dict:
    return {s: emap.get(m[f"entry_{s}_id"], {}).get("name") or (models.get_entry(m[f"entry_{s}_id"]) or {}).get("name", tr("TBD"))
            for s in ("a", "b")}


def _players(m) -> dict:
    p = models.side_players(m)
    return {s: [x["name"] for x in p[s]] or ["?"] for s in ("a", "b")}


def _server_name(state, players):
    team = players[state["serving"]]
    return team[min(state["server_idx"], len(team) - 1)]


def _event_message(events, state, score, names, players) -> str | None:
    srv = state["serving"]
    if "game_over" in events:
        w = state["game_over"]
        return tr("Game to {team} — confirm it below (or Undo if that rally was wrong).",
                  team=names[w])
    if "switch_ends" in events:
        return tr("🔄 Switch ends now! Both sides change ends.")
    if "side_out" in events:
        return tr("Side out — {team} to serve: {server}.", team=names[srv],
                  server=_server_name(state, players))
    if "second_server" in events:
        return tr("Second server: {server}.", server=_server_name(state, players))
    return None


# --------------------------------------------------------------------------
# callbacks (run before the rerun — one tap, one redraw)
# --------------------------------------------------------------------------

def _cb_rally(mid, side, names_key):
    try:
        events = models.record_rally(mid, side, actor=ui.admin_name())
        m = models.get_match(mid)
        state = models.serve_state(m)
        score = (m["cur_a"], m["cur_b"])
        names = st.session_state.get(names_key, {"a": "A", "b": "B"})
        msg = _event_message(events, state, score, names, _players(m))
        if msg:
            _flash("big" if ("switch_ends" in events or "game_over" in events) else "info", msg)
    except models.RuleError as e:
        _flash("error", str(e))


def _cb(fn, *args, ok: str | None = None):
    try:
        fn(*args, actor=ui.admin_name())
        if ok:
            _flash("info", ok)
    except models.RuleError as e:
        _flash("error", str(e))


def _cb_confirm(mid):
    try:
        finished = models.confirm_current_game(mid, actor=ui.admin_name())
        _flash("big", tr("🏆 Match complete.") if finished else
               tr("Game locked in. New game: sides change ends — check the serve below."))
    except models.RuleError as e:
        _flash("error", str(e))


def _cb_adjust(mid, side, delta):
    try:
        models.adjust_point(mid, side, delta, actor=ui.admin_name())
    except models.RuleError as e:
        _flash("error", str(e))


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def court_html(state, score, players, names, rule) -> str:
    left = "a" if state["a_left"] else "b"
    right_side = rules.other(left)
    sc = {"a": score[0], "b": score[1]}
    allowed = rules.timeouts_allowed(rule)

    def box(side, court, where):
        # which player of `side` stands in `court` ("right"/"left")?
        idx = None
        for i in range(len(players[side])):
            if rules.court_of(state, score, side, i) == court:
                idx = i
                break
        if not state["doubles"]:
            idx = 0 if rules.court_of(state, score, side, 0) == court else None
        serving = (idx is not None and side == state["serving"] and idx == state["server_idx"])
        name = players[side][idx] if idx is not None and idx < len(players[side]) else ""
        tag = tr("Right · even") if court == "right" else tr("Left · odd")
        ball = '<span class="pk-ball"></span>' if serving else ""
        return (f'<div class="pk-box {where}{" srv" if serving else ""}">'
                f'<div class="pk-ctag">{tag}</div>'
                f'<div class="pk-pname">{ball}{_esc(name)}</div></div>')

    def half(side, pos):
        # The left-hand side faces the net on its right, so its right court is
        # the bottom box; the right-hand side's right court is the top box.
        top, bot = ("left", "right") if pos == "L" else ("right", "left")
        to = state["timeouts"][side]
        head = (f'<div class="pk-hh" style="background:{TEAM_COLOR[side]}">'
                f'<div><div class="tn">{_esc(names[side])}</div>'
                f'<div class="to">{tr("Timeouts {a}/{b}", a=to, b=allowed)}</div></div>'
                f'<div class="sc">{sc[side]}</div></div>')
        return (f'<div class="pk-half {pos}">{head}{box(side, top, "top")}{box(side, bot, "bot")}'
                f'<div class="pk-kit">{tr("KITCHEN")}</div></div>')

    return (f'<div class="pk-ct">{half(left, "L")}<div class="pk-net"></div>'
            f'{half(right_side, "R")}</div>')


def call_html(state, score, players, names, rule, gw, best_of) -> str:
    srv = state["serving"]
    call = rules.score_call(state, score)
    court = rules.server_court(state, score)
    server = _server_name(state, players)
    sub = tr("<b>{server}</b> serves from the <b>{court}</b> court", server=_esc(server),
             court=tr("right") if court == "right" else tr("left"))
    if state["doubles"] and state["system"] == rules.SIDE_OUT:
        sub += " · " + tr("server {n}", n=state["server_no"])
    badges = []
    if state.get("game_over"):
        badges.append(f'<span class="pk-badge go">{tr("Game — {team}", team=_esc(names[state["game_over"]]))}</span>')
    else:
        need = best_of // 2 + 1
        for side in rules.game_point_for(state, score, rule):
            if gw[side] + 1 >= need:
                badges.append(f'<span class="pk-badge mp">{tr("Match point — {team}", team=_esc(names[side]))}</span>')
            else:
                badges.append(f'<span class="pk-badge gp">{tr("Game point — {team}", team=_esc(names[side]))}</span>')
    warn = rules.position_warning(state, score)
    if warn:
        badges.append(f'<span class="pk-badge warn">{_esc(warn)}</span>')
    return (f'<div class="pk-call">{_esc(call)}</div><div class="pk-callsub">{sub}</div>'
            f'<div class="pk-badges">{"".join(badges)}</div>')


def _key_hash(s: str) -> str:
    return str(zlib.crc32(s.encode("utf-8")))


def names_editor(m, kp: str):
    """Fix a misspelt name right before (or during) the match. Registered
    players are renamed everywhere — every event, draw, standings table and
    the live board — without touching seeds, draws or results."""
    sp = models.side_players(m)
    with st.form(f"{kp}_names_form"):
        st.caption(tr("Corrects the name everywhere it appears — other events, draws, standings, "
                      "the live board. Seeds, draw positions and results stay exactly as they are."))
        cols = st.columns(2)
        new = {"a": [], "b": []}
        for col, side in zip(cols, ("a", "b")):
            with col:
                st.markdown("**" + tr("Side {s}", s=side.upper()) + "**")
                for i, p in enumerate(sp[side]):
                    new[side].append(st.text_input(
                        tr("Side {s} player {n}", s=side.upper(), n=i + 1), value=p["name"],
                        key=f"{kp}_nm_{side}_{i}_{_key_hash(p['name'])}"))
        if st.form_submit_button(tr("Save names"), type="primary"):
            changed = 0
            try:
                for side in ("a", "b"):
                    if not sp[side]:
                        continue
                    if sp[side][0]["id"] is None:          # quick match: names live on the entry
                        if [p["name"] for p in sp[side]] != [" ".join(n.split()) for n in new[side]]:
                            models.rename_entry_names(m[f"entry_{side}_id"], new[side],
                                                      actor=ui.admin_name())
                            changed += 1
                    else:
                        for p, n in zip(sp[side], new[side]):
                            if " ".join(n.split()) != p["name"]:
                                models.rename_player(p["id"], n, actor=ui.admin_name())
                                changed += 1
                st.session_state["ref_flash"] = ("info", tr("{n} name(s) updated everywhere.", n=changed)
                                                 if changed else tr("No names changed."))
                st.rerun()
            except models.RuleError as e:
                st.error(str(e))


def serve_setup(m, kp: str, state, names, players, *, before_start: bool):
    """Who serves first and who starts in the right (even) court. Before the
    match this feeds `start_match`; at 0-0 of any game it can still be changed."""
    first = st.radio(tr("Serves first"), ["a", "b"], horizontal=True,
                     index=0 if (state or {}).get("first_serving", "a") == "a" else 1,
                     format_func=lambda s: names[s], key=f"{kp}_first")
    right = {"a": 0, "b": 0}
    if len(players["a"]) == 2 or len(players["b"]) == 2:
        st.caption(tr("Who starts in the **right (even) court**? They serve first for their side."))
        cols = st.columns(2)
        for col, side in zip(cols, ("a", "b")):
            opts = list(range(len(players[side])))
            cur = (state or {}).get("start_right", {}).get(side, 0)
            right[side] = col.radio(names[side], opts, index=min(cur, len(opts) - 1),
                                    format_func=lambda i, s=side: players[s][i],
                                    key=f"{kp}_right_{side}")
    if not before_start:
        if st.button(tr("Save serve setup"), key=f"{kp}_ref_setup"):
            _cb(models.setup_serve, m["id"], first, right, ok=tr("Serve setup saved."))
            st.rerun()
    return first, right


def fullscreen_toggle(kp: str):
    on = st.toggle(tr("Tablet full-screen (hide the menu)"), value=st.session_state.get("ref_fullscreen", True),
                   key=f"{kp}_fs")
    st.session_state["ref_fullscreen"] = on
    if on:
        st.markdown(FULLSCREEN_CSS, unsafe_allow_html=True)


def render_live(m, ev, emap, kp: str, manual_form=None):
    """The live referee board for one match."""
    st.markdown(REF_CSS, unsafe_allow_html=True)
    state = models.ensure_serve_state(m)
    score = (int(m["cur_a"]), int(m["cur_b"]))
    rule = models.scoring_rule(ev)
    players = _players(m)
    names = team_names(m, emap)
    names_key = f"{kp}_names_cache"
    st.session_state[names_key] = names
    gw = models.games_won(m["id"])
    game_no = models.current_game_no(m["id"])
    deciding = rules.is_deciding_game(gw, m["best_of"])

    system_label = tr("Side-out") if state["system"] == rules.SIDE_OUT else tr("Rally scoring")
    meta = [tr("Game {a} of {b}", a=game_no, b=m["best_of"]) + (" · " + tr("decider") if deciding else ""),
            tr("Games {a}–{b}", a=gw["a"], b=gw["b"]), i18n.preset_label(rule), system_label]
    if m.get("court"):
        meta.append(m["court"])
    st.markdown('<div class="pk-ref-meta">' + "".join(f'<span class="chip">{_esc(x)}</span>' for x in meta)
                + "</div>", unsafe_allow_html=True)

    _show_flash()
    st.markdown(call_html(state, score, players, names, rule, gw, m["best_of"]), unsafe_allow_html=True)
    st.markdown(court_html(state, score, players, names, rule), unsafe_allow_html=True)

    left = "a" if state["a_left"] else "b"
    right_side = rules.other(left)
    over = bool(state.get("game_over"))
    c1, c2 = st.columns(2, gap="medium")
    for col, side in ((c1, left), (c2, right_side)):
        col.button(tr("{team} won the rally", team=names[side]), key=f"{kp}_rally_{side}",
                   on_click=_cb_rally, args=(m["id"], side, names_key),
                   disabled=over, width="stretch")

    if over:
        st.button(tr("✅ Confirm game to {team}  ({a}–{b})", team=names[state["game_over"]],
                     a=score[0], b=score[1]),
                  key=f"{kp}_confirm", type="primary", width="stretch",
                  on_click=_cb_confirm, args=(m["id"],))

    allowed = rules.timeouts_allowed(rule)
    b1, b2, b3, b4 = st.columns(4)
    b1.button(tr("↶ Undo"), key=f"{kp}_ref_undo", width="stretch",
              on_click=_cb, args=(models.undo_rally, m["id"]), kwargs={"ok": tr("Undone.")})
    b2.button(tr("⏱ Timeout ◀ ({a}/{b})", a=state["timeouts"][left], b=allowed),
              key=f"{kp}_ref_to_{left}", width="stretch",
              on_click=_cb, args=(models.call_timeout, m["id"], left),
              kwargs={"ok": tr("Timeout — {team} (1 minute).", team=names[left])})
    b3.button(tr("⏱ Timeout ▶ ({a}/{b})", a=state["timeouts"][right_side], b=allowed),
              key=f"{kp}_ref_to_{right_side}", width="stretch",
              on_click=_cb, args=(models.call_timeout, m["id"], right_side),
              kwargs={"ok": tr("Timeout — {team} (1 minute).", team=names[right_side])})
    b4.button(tr("⇄ Switch ends"), key=f"{kp}_ref_switch", width="stretch",
              on_click=_cb, args=(models.switch_ends, m["id"]))

    st.write("")
    if not state.get("rallies") and score == (0, 0):
        with st.expander(tr("🎾 Serve setup for this game"), expanded=False):
            serve_setup(m, kp, state, names, players, before_start=False)
    with st.expander(tr("✏️ Edit player names")):
        names_editor(m, kp)
    with st.expander(tr("🔧 Correct the score by hand")):
        st.caption(tr("For fixing a mistake the rules can't undo. Rally buttons and Undo are "
                      "the normal way to score."))
        cc = st.columns(4)
        cc[0].button(f"{names['a'][:14]} −1", key=f"{kp}_ref_am", width="stretch",
                     on_click=_cb_adjust, args=(m["id"], "a", -1))
        cc[1].button(f"{names['a'][:14]} +1", key=f"{kp}_ref_ap", width="stretch",
                     on_click=_cb_adjust, args=(m["id"], "a", 1))
        cc[2].button(f"{names['b'][:14]} −1", key=f"{kp}_ref_bm", width="stretch",
                     on_click=_cb_adjust, args=(m["id"], "b", -1))
        cc[3].button(f"{names['b'][:14]} +1", key=f"{kp}_ref_bp", width="stretch",
                     on_click=_cb_adjust, args=(m["id"], "b", 1))
        court = st.text_input(tr("Court"), value=m["court"] or "", key=f"{kp}_court",
                              placeholder=tr("e.g. Court 3"))
        if st.button(tr("Save court"), key=f"{kp}_courtsave"):
            models.set_court(m["id"], court or None, actor=ui.admin_name())
            st.rerun()
        if models.get_games(m["id"]):
            st.button(tr("Undo the last confirmed game"), key=f"{kp}_ref_undogame",
                      on_click=_cb, args=(models.undo_last_game, m["id"]),
                      kwargs={"ok": tr("Last game reopened.")})
    if manual_form:
        with st.expander(tr("Retire a side, or type the whole score in by hand")):
            manual_form()


def render_prematch(m, ev, emap, kp: str):
    """Before the first serve: court, who serves, starting positions, names."""
    st.markdown(REF_CSS, unsafe_allow_html=True)
    _show_flash()
    rule = models.scoring_rule(ev)
    names = team_names(m, emap)
    players = _players(m)
    system_label = tr(rules.SCORING_SYSTEMS[models.scoring_system(ev)])
    st.markdown('<div class="pk-ref-meta">' + "".join(
        f'<span class="chip">{_esc(x)}</span>'
        for x in (i18n.preset_label(rule), tr("Best of {n}", n=m["best_of"]), system_label)) + "</div>",
        unsafe_allow_html=True)
    st.markdown(f'<div class="pk-call" style="font-size:clamp(1.6rem,4vw,2.6rem)">'
                f'{_esc(names["a"])} <span style="color:var(--mute)">{tr("vs")}</span> {_esc(names["b"])}</div>',
                unsafe_allow_html=True)

    with st.expander(tr("✏️ Check / edit player names before the match"), expanded=False):
        names_editor(m, kp)

    court = st.text_input(tr("Court"), value=m["court"] or "", key=f"{kp}_court0",
                          placeholder=tr("e.g. Court 3"))
    first, right = serve_setup(m, kp, None, names, players, before_start=True)
    if st.button(tr("▶ Start match"), key=f"{kp}_start", type="primary", width="stretch"):
        try:
            models.start_match(m["id"], actor=ui.admin_name(), court=court or None,
                               first_serving=first, right=right)
            models.claim_match(m["id"], ui.admin_name())
            st.rerun()
        except models.RuleError as e:
            st.error(str(e))
