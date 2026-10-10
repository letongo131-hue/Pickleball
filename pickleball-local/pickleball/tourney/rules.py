"""Pickleball scoring rules — the referee's brain, as pure functions.

Nothing here touches the database or Streamlit: every function takes the
current serve state and score and returns new ones, so each rule can be
tested on its own and the referee view only ever asks "who won the rally?".

Two scoring systems:

Traditional side-out scoring (USA Pickleball default)
  * Only the serving side scores.
  * Doubles: each side gets two servers ("server 1", "server 2") before a
    side out — except the very first service turn of a game, which starts
    as server 2 (the famous "0-0-2"), so the first serving side gets one
    server only.
  * When the serving side wins a rally it scores and the server switches
    courts with their partner and serves again. Receivers never switch.
  * When server 1 loses a rally, their partner serves from wherever the
    partner is standing. When server 2 loses, it's a side out and the
    player in the right (even) court of the new serving side serves first.
  * Score is called serving score - receiving score - server number.
  * Singles: the server serves from the right when their own score is even
    and from the left when odd; a lost rally is a side out.

Rally scoring
  * Every rally scores a point for whoever wins it.
  * Serving side wins: point, server switches courts and serves again.
  * Receiving side wins: point and the serve. Players do not switch; the
    player standing in the court matching the new serving side's score
    (even = right, odd = left) serves. One server per side, so the call is
    just serving score - receiving score.

Both systems
  * A game ends at the target with the required lead (or at the cap) — see
    `validate_game`.
  * In the deciding game (game 1 of a one-game match, game 3 of best of 3,
    game 5 of best of 5) sides switch ends when the first side reaches 6 in
    a game to 11, 8 in a game to 15, 11 in a game to 21.
  * Sides switch ends between games, and whoever received first in the
    previous game serves first in the next.
  * Timeouts: 2 per side per game to 11 or 15, 3 per game to 21.

State is a plain dict (stored as JSON on the match):

    serving        "a" | "b"   side currently serving
    server_no      1 | 2       side-out doubles only
    server_idx     0 | 1       which player of the serving side is serving
    right          {"a": idx, "b": idx}   player standing in the right court
    start_right    same, as the game started (for the even-score check)
    first_serving  side that served first this game
    a_left         True when side A is on the left end from the referee's view
    ends_switched  mid-game switch already done
    timeouts       {"a": n, "b": n} used this game
    game_over      None | "a" | "b"
    rallies        rallies played this game
"""

from __future__ import annotations

import copy

from .i18n import tr

SIDE_OUT = "side_out"
RALLY = "rally"

SCORING_SYSTEMS = {
    SIDE_OUT: "Side-out scoring (only the serving side scores)",
    RALLY: "Rally scoring (a point on every rally)",
}

SIDES = ("a", "b")


def other(side: str) -> str:
    return "b" if side == "a" else "a"


# --------------------------------------------------------------------------
# Game-level rules
# --------------------------------------------------------------------------

def validate_game(a: int, b: int, rule: dict) -> str | None:
    """None if a-b is a legal finished game under `rule`, else why not."""
    target, win_by, cap = rule["target"], rule["win_by"], rule["cap"]
    if a < 0 or b < 0:
        return tr("Scores cannot be negative.")
    if a == b:
        return tr("A game cannot end level.")
    hi, lo = max(a, b), min(a, b)
    if cap and hi == cap:
        return None if hi - lo >= 1 else tr("Capped game still needs a one-point margin.")
    if hi < target:
        return tr("Winning score must reach {n}.", n=target)
    if hi > target and hi - lo != win_by:
        return tr("Past {n} the game ends the moment someone leads by {w}.", n=target, w=win_by)
    if hi - lo < win_by:
        return tr("Winner must lead by {w}.", w=win_by)
    if cap and hi > cap:
        return tr("Score is capped at {n}.", n=cap)
    return None


def game_winner(a: int, b: int, rule: dict) -> str | None:
    if validate_game(a, b, rule) is None:
        return "a" if a > b else "b"
    return None


def switch_point(rule: dict) -> int:
    """Score at which ends are switched mid-game in a deciding game."""
    return (rule["target"] + 1) // 2          # 11 -> 6, 15 -> 8, 21 -> 11


def timeouts_allowed(rule: dict) -> int:
    return 3 if rule["target"] >= 21 else 2


def is_deciding_game(games_won: dict, best_of: int) -> bool:
    need = best_of // 2 + 1
    return games_won["a"] == need - 1 and games_won["b"] == need - 1


# --------------------------------------------------------------------------
# Serve state
# --------------------------------------------------------------------------

def new_game(*, doubles: bool, system: str = SIDE_OUT, first_serving: str = "a",
             right: dict | None = None, a_left: bool = True) -> dict:
    right = {"a": 0, "b": 0} if not doubles else dict(right or {"a": 0, "b": 0})
    side_out_doubles = doubles and system == SIDE_OUT
    return {
        "v": 1, "system": system, "doubles": doubles,
        "serving": first_serving, "first_serving": first_serving,
        # 0-0-2: the first serving turn of a side-out doubles game is server 2.
        "server_no": 2 if side_out_doubles else 1,
        "server_idx": right[first_serving],
        "right": right, "start_right": dict(right),
        "a_left": a_left, "ends_switched": False,
        "timeouts": {"a": 0, "b": 0},
        "game_over": None, "rallies": 0,
    }


def next_game(prev: dict) -> dict:
    """Serve state for the following game: sides change ends, whoever received
    first last game serves first now, players start where they started."""
    return new_game(doubles=prev["doubles"], system=prev["system"],
                    first_serving=other(prev["first_serving"]),
                    right=prev.get("start_right") or prev["right"],
                    a_left=not prev["a_left"])


def reconfigure(state: dict, *, first_serving: str | None = None,
                right: dict | None = None, a_left: bool | None = None) -> dict:
    """Change who serves first / who starts on the right — only meaningful
    before the first rally of a game."""
    s = new_game(doubles=state["doubles"], system=state["system"],
                 first_serving=first_serving or state["first_serving"],
                 right=right or state["start_right"],
                 a_left=state["a_left"] if a_left is None else a_left)
    return s


def apply_rally(state: dict, score: tuple[int, int], winner: str, rule: dict,
                deciding: bool = False) -> tuple[dict, tuple[int, int], list[str]]:
    """The heart of it: the rally was won by `winner` ("a"/"b").

    Returns (new_state, new_score, events). Events are any of:
    "point", "second_server", "side_out", "switch_ends", "game_over".
    """
    if winner not in SIDES:
        raise ValueError("winner must be 'a' or 'b'")
    if state.get("game_over"):
        raise ValueError(tr("This game is already over — confirm it or undo."))
    s = copy.deepcopy(state)
    sc = {"a": int(score[0]), "b": int(score[1])}
    events: list[str] = []
    srv = s["serving"]
    doubles = s["doubles"]

    if s["system"] == SIDE_OUT:
        if winner == srv:
            sc[srv] += 1
            events.append("point")
            if doubles:
                s["right"][srv] = 1 - s["right"][srv]       # server switches courts
        elif doubles and s["server_no"] == 1:
            s["server_no"] = 2
            s["server_idx"] = 1 - s["server_idx"]            # partner serves from where they stand
            events.append("second_server")
        else:
            new = other(srv)
            s["serving"] = new
            s["server_no"] = 1
            s["server_idx"] = s["right"][new]                # right-court player starts
            events.append("side_out")
    else:   # rally scoring
        sc[winner] += 1
        events.append("point")
        if winner == srv:
            if doubles:
                s["right"][srv] = 1 - s["right"][srv]
        else:
            s["serving"] = winner
            events.append("side_out")
            if doubles:
                even = sc[winner] % 2 == 0
                s["server_idx"] = s["right"][winner] if even else 1 - s["right"][winner]

    s["rallies"] = s.get("rallies", 0) + 1

    if deciding and not s["ends_switched"] and max(sc.values()) >= switch_point(rule):
        s["ends_switched"] = True
        s["a_left"] = not s["a_left"]
        events.append("switch_ends")

    gw = game_winner(sc["a"], sc["b"], rule)
    if gw:
        s["game_over"] = gw
        events.append("game_over")
    return s, (sc["a"], sc["b"]), events


def recheck_game_over(state: dict, score: tuple[int, int], rule: dict) -> dict:
    """After a manual score correction, re-derive whether the game is over."""
    s = copy.deepcopy(state)
    s["game_over"] = game_winner(score[0], score[1], rule)
    return s


def use_timeout(state: dict, side: str, rule: dict) -> dict:
    if state["timeouts"][side] >= timeouts_allowed(rule):
        raise ValueError(tr("No timeouts left (each side gets {n} per game).", n=timeouts_allowed(rule)))
    s = copy.deepcopy(state)
    s["timeouts"][side] += 1
    return s


def toggle_ends(state: dict) -> dict:
    s = copy.deepcopy(state)
    s["a_left"] = not s["a_left"]
    return s


# --------------------------------------------------------------------------
# What the referee sees
# --------------------------------------------------------------------------

def court_of(state: dict, score: tuple[int, int], side: str, idx: int) -> str:
    """'right' or 'left' — where this player is standing right now."""
    sc = {"a": score[0], "b": score[1]}
    if state["doubles"]:
        return "right" if state["right"][side] == idx else "left"
    # Singles: both players stand in the court matching the server's score.
    return "right" if sc[state["serving"]] % 2 == 0 else "left"


def server_court(state: dict, score: tuple[int, int]) -> str:
    return court_of(state, score, state["serving"], state["server_idx"])


def score_call(state: dict, score: tuple[int, int]) -> str:
    sc = {"a": score[0], "b": score[1]}
    srv = state["serving"]
    call = f"{sc[srv]} – {sc[other(srv)]}"
    if state["doubles"] and state["system"] == SIDE_OUT:
        call += f" – {state['server_no']}"
    return call


def game_point_for(state: dict, score: tuple[int, int], rule: dict) -> list[str]:
    """Sides that would win the game by winning the next rally."""
    if state.get("game_over"):
        return []
    out = []
    for side in SIDES:
        try:
            s2, _, ev = apply_rally(state, score, side, rule)
        except ValueError:
            continue
        if "game_over" in ev and s2["game_over"] == side:
            out.append(side)
    return out


def position_warning(state: dict, score: tuple[int, int]) -> str | None:
    """Side-out doubles sanity check the referee normally does by eye: with an
    even score, the side's starting server must be in the right court."""
    if not (state["doubles"] and state["system"] == SIDE_OUT):
        return None
    sc = {"a": score[0], "b": score[1]}
    for side in SIDES:
        expect_right = state["start_right"][side] if sc[side] % 2 == 0 else 1 - state["start_right"][side]
        if state["right"][side] != expect_right:
            return tr("Side {s} positions don't match their score — check who is on the right.", s=side.upper())
    return None
