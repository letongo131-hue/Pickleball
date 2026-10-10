"""Shared vocabulary for the tournament engine."""

CATEGORIES = {
    "MS": "Men's Singles",
    "WS": "Women's Singles",
    "MD": "Men's Doubles",
    "WD": "Women's Doubles",
    "XD": "Mixed Doubles",
    "QM": "Quick Match",
}

CATEGORY_ORDER = ["MS", "WS", "MD", "WD", "XD"]

# How many players make up one entry in each category.
TEAM_SIZE = {"MS": 1, "WS": 1, "MD": 2, "WD": 2, "XD": 2, "QM": 2}

# Expected genders per entry. None = no constraint.
GENDER_RULE = {
    "MS": ("M",),
    "WS": ("F",),
    "MD": ("M", "M"),
    "WD": ("F", "F"),
    "XD": ("M", "F"),
}

FORMATS = {
    "round_robin": "Round Robin",
    "swiss": "Swiss",
    "single_elim": "Single Elimination",
    "double_elim": "Double Elimination",
    "pool_playoff": "Pool Play → Playoffs",
}

FORMAT_ORDER = ["round_robin", "swiss", "single_elim", "double_elim", "pool_playoff"]

FORMAT_HELP = {
    "round_robin": "Everyone plays everyone once. Best for 4–10 entries.",
    "swiss": "Fixed number of rounds, paired by record each round, no eliminations.",
    "single_elim": "Lose once and you're out. Fastest format.",
    "double_elim": "Losers drop to a consolation bracket and can still win.",
    "pool_playoff": "Round robin pools first, top finishers advance to a knockout bracket.",
}

# Match lifecycle
STATUS_PENDING = "pending"      # waiting on entries or on a court
STATUS_LIVE = "live"            # in progress
STATUS_DONE = "done"            # score recorded
STATUS_BYE = "bye"              # walkover, no play
STATUS_VOID = "void"            # slot never fills (bye cascade)

OPEN_STATUSES = (STATUS_PENDING, STATUS_LIVE)

# Bracket stages
STAGE_MAIN = "main"
STAGE_WB = "wb"
STAGE_LB = "lb"
STAGE_GF = "gf"
STAGE_POOL = "pool"
STAGE_PLAYOFF = "playoff"

STAGE_LABEL = {
    STAGE_MAIN: "Main draw",
    STAGE_WB: "Winners bracket",
    STAGE_LB: "Losers bracket",
    STAGE_GF: "Grand final",
    STAGE_POOL: "Pool play",
    STAGE_PLAYOFF: "Playoffs",
}

POOL_NAMES = list("ABCDEFGHIJKL")

SCORING_PRESETS = {
    "11_first": {"target": 11, "win_by": 1, "cap": 11,
                 "label": "To 11 (first to 11 wins, no win-by-2)"},
    "11_rally_2": {"target": 11, "win_by": 2, "cap": None, "label": "To 11, win by 2"},
    "11_cap_15": {"target": 11, "win_by": 2, "cap": 15, "label": "To 11, win by 2, cap 15"},
    "15_first": {"target": 15, "win_by": 1, "cap": 15,
                 "label": "To 15 (first to 15 wins, no win-by-2)"},
    "15_rally_2": {"target": 15, "win_by": 2, "cap": None, "label": "To 15, win by 2"},
    "15_cap_21": {"target": 15, "win_by": 2, "cap": 21, "label": "To 15, win by 2, cap 21"},
    "21_rally_2": {"target": 21, "win_by": 2, "cap": None, "label": "To 21, win by 2"},
}

# --------------------------------------------------------------------------
# Roles
# --------------------------------------------------------------------------
# admin    — full access: tournament/event setup, players, courts, fixtures,
#            scoring, everything.
# referee  — the scoring desk only: start matches, enter/adjust scores,
#            correct results. Every save is attributed and logged.
# viewer   — read-only everywhere (Live, Draws & standings, Venue display).
#            This is also the default for anyone who has not signed in.
ROLE_ADMIN = "admin"
ROLE_REFEREE = "referee"
ROLE_VIEWER = "viewer"

ROLE_LABEL = {ROLE_ADMIN: "Admin", ROLE_REFEREE: "Referee", ROLE_VIEWER: "Viewer"}
