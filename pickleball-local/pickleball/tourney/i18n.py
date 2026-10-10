"""Two-language support: English (what the code was written in) and
Vietnamese, since this desk runs Vietnamese tournaments for Vietnamese
admins, referees, and players.

`t(key)` looks up the current language from session state; `category_label`
and `format_label` do the same for the event category/format names, which
show up on almost every page. Call `set_lang()` from the sidebar to switch.

This covers the pages every admin, referee, and spectator sees constantly —
navigation, the Live board, sign-in, and every category/format name. Deeper
admin-only configuration (Setup's advanced options, the custom bracket
builder, Fixtures editing) is still English-only; extending coverage there
is a matter of adding more keys here and routing more call sites through
`t()`, not a structural change.

Streamlit is optional here. Inside a running Streamlit app the language is
stored per browser session in `st.session_state`; anywhere else (plain
Python, the engine tests, a script) it falls back to a module-level value,
so the tournament engine can be imported and tested without Streamlit
installed at all.
"""

from __future__ import annotations

import os
import re

# Vietnamese unless overridden (the test suite sets PICKLEBALL_DEFAULT_LANG=en
# so its English label lookups keep working; a dedicated test checks Vietnamese).
DEFAULT_LANG = os.environ.get("PICKLEBALL_DEFAULT_LANG", "vi")

LANG_LABEL = {"vi": "Tiếng Việt", "en": "English"}

# Used only outside a Streamlit session (tests, scripts).
_FALLBACK_STATE: dict[str, str] = {}

STRINGS: dict[str, dict[str, str]] = {
    # --- navigation ----------------------------------------------------
    "nav.follow_along": {"en": "Follow along", "vi": "Theo dõi"},
    "nav.run_event": {"en": "Run the event", "vi": "Điều hành giải đấu"},
    "nav.live": {"en": "Live", "vi": "Trực tiếp"},
    "nav.draws": {"en": "Draws & standings", "vi": "Bốc thăm & Bảng xếp hạng"},
    "nav.venue": {"en": "Venue display", "vi": "Màn hình sân đấu"},
    "nav.scoring": {"en": "Scoring desk", "vi": "Bàn tính điểm"},
    "nav.quick": {"en": "Quick match", "vi": "Trận đấu nhanh"},
    "nav.courts": {"en": "Courts", "vi": "Sân đấu"},
    "nav.fixtures": {"en": "Fixtures", "vi": "Lịch thi đấu"},
    "nav.players": {"en": "Players & entries", "vi": "Vận động viên & Đăng ký"},
    "nav.setup": {"en": "Setup", "vi": "Thiết lập"},

    # --- sign-in ---------------------------------------------------------
    "signin.title": {"en": "Sign in", "vi": "Đăng nhập"},
    "signin.name": {"en": "Your name", "vi": "Tên của bạn"},
    "signin.role": {"en": "Role", "vi": "Vai trò"},
    "signin.passcode": {"en": "Passcode", "vi": "Mã bảo mật"},
    "signin.button": {"en": "Sign in", "vi": "Đăng nhập"},
    "signin.signout": {"en": "Sign out", "vi": "Đăng xuất"},
    "signin.name_required": {"en": "Enter your name so results are attributed correctly.",
                             "vi": "Nhập tên của bạn để kết quả được ghi nhận chính xác."},
    "signin.wrong_passcode": {"en": "That passcode is not right.", "vi": "Mã bảo mật không đúng."},
    "signin.viewer_note": {
        "en": "Viewers don't need to sign in — everyone can watch the live board and "
              "standings read-only.",
        "vi": "Người xem không cần đăng nhập — ai cũng có thể xem bảng trực tiếp và "
              "bảng xếp hạng."},
    "signin.signed_in_as": {"en": "Signed in as", "vi": "Đã đăng nhập với tên"},
    "signin.several_people": {
        "en": "Several people can be signed in at once. Every save is stamped with your "
              "name and checked against the last one.",
        "vi": "Nhiều người có thể đăng nhập cùng lúc. Mỗi lần lưu đều ghi lại tên bạn và "
              "được đối chiếu với lần lưu trước đó."},

    # --- roles -------------------------------------------------------------
    "role.admin": {"en": "Admin", "vi": "Quản trị viên"},
    "role.referee": {"en": "Referee", "vi": "Trọng tài"},
    "role.viewer": {"en": "Viewer", "vi": "Người xem"},

    # --- sidebar / general ---------------------------------------------
    "tournament.label": {"en": "Tournament", "vi": "Giải đấu"},
    "theme.label": {"en": "Look", "vi": "Giao diện"},
    "lang.label": {"en": "Language", "vi": "Ngôn ngữ"},
    "brand.sub": {"en": "tournament desk", "vi": "bàn điều hành giải đấu"},

    # --- Live board ------------------------------------------------------
    "live.on_court": {"en": "On court", "vi": "Đang thi đấu"},
    "live.next_up": {"en": "Next up", "vi": "Sắp thi đấu"},
    "live.just_finished": {"en": "Just finished", "vi": "Vừa kết thúc"},
    "live.rankings": {"en": "Rankings", "vi": "Bảng xếp hạng"},
    "live.nothing_on_court": {"en": "Nothing is on court.", "vi": "Hiện không có trận nào đang thi đấu."},
    "live.no_matches_ready": {"en": "No matches are ready to call.",
                              "vi": "Chưa có trận nào sẵn sàng để gọi."},
    "live.no_results": {"en": "No results in yet.", "vi": "Chưa có kết quả nào."},
    "live.no_events": {"en": "This tournament has no events yet. Add them on the Setup page.",
                       "vi": "Giải đấu chưa có nội dung thi đấu. Thêm nội dung ở trang Thiết lập."},
    "live.more_waiting": {"en": "more waiting", "vi": "trận khác đang chờ"},
    "live.standings_so_far": {"en": "Standings so far", "vi": "Bảng xếp hạng hiện tại"},
    "live.final_standings": {"en": "Final standings", "vi": "Bảng xếp hạng chung cuộc"},
    "live.no_entries": {"en": "No entries yet.", "vi": "Chưa có đội/vận động viên đăng ký."},

    # --- match status words, used all over -----------------------------
    "status.live": {"en": "Live", "vi": "Đang đấu"},
    "status.pending": {"en": "Pending", "vi": "Chưa đấu"},
    "status.done": {"en": "Done", "vi": "Đã xong"},
}

# --- category / format names, shown on nearly every page -------------------
CATEGORIES_VI = {
    "MS": "Đơn nam", "WS": "Đơn nữ", "MD": "Đôi nam", "WD": "Đôi nữ",
    "XD": "Đôi nam nữ", "QM": "Trận đấu nhanh",
}
FORMATS_VI = {
    "round_robin": "Vòng tròn tính điểm",
    "single_elim": "Loại trực tiếp",
    "double_elim": "Loại kép",
    "pool_playoff": "Vòng bảng → Loại trực tiếp",
    "swiss": "Hệ Thụy Sĩ",
}


def _state():
    """Where the chosen language lives: Streamlit's per-session state when a
    script is actually running under Streamlit, otherwise a plain dict."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx(suppress_warning=True) is not None:
            import streamlit as st
            return st.session_state
    except Exception:
        pass
    return _FALLBACK_STATE


def t(key: str) -> str:
    entry = STRINGS.get(key)
    if not entry:
        return key
    return entry.get(current_lang(), entry.get("en", key))


def current_lang() -> str:
    return _state().get("ui_lang", DEFAULT_LANG)


def set_lang(lang: str):
    if lang in ("en", "vi"):
        _state()["ui_lang"] = lang


def lang_options() -> dict[str, str]:
    return dict(LANG_LABEL)


def category_label(code: str, fallback: str) -> str:
    if current_lang() == "vi" and code in CATEGORIES_VI:
        return CATEGORIES_VI[code]
    return fallback


def format_label(code: str, fallback: str) -> str:
    if current_lang() == "vi" and code in FORMATS_VI:
        return FORMATS_VI[code]
    return fallback


# ==========================================================================
# tr(): every other user-facing string in the app
# ==========================================================================
# Source strings are the English text itself, so the code stays readable and
# a missing translation simply falls back to English. All Vietnamese lives in
# tourney/vi.py. tests/test_i18n.py parses the source code, collects every
# tr("...") literal and fails if one has no Vietnamese entry — so a new string
# can't quietly ship untranslated.
#
# Use placeholders, never f-strings, inside tr():
#     tr("{n} entries", n=len(entries))

MISSING: set[str] = set()


def tr(text: str, **kw) -> str:
    out = text
    if current_lang() == "vi":
        from .vi import VI
        out = VI.get(text)
        if out is None:
            MISSING.add(text)
            out = text
    if kw:
        try:
            return out.format(**kw)
        except (KeyError, IndexError, ValueError):
            return text.format(**kw)
    return out


def cat(code: str) -> str:
    from .constants import CATEGORIES
    return category_label(code, CATEGORIES.get(code, code))


def fmt(code: str) -> str:
    from .constants import FORMATS
    return format_label(code, FORMATS.get(code, code))


def preset_label(rule: dict) -> str:
    return tr(rule["label"])


_STATUS_EN = {"setup": "Setting up", "running": "In progress", "complete": "Complete",
              "pending": "Pending", "live": "Live", "done": "Done", "bye": "Walkover",
              "void": "Void", "active": "Active", "withdrawn": "Withdrawn",
              "open": "Open", "closed": "Closed"}


def status(code: str | None) -> str:
    return tr(_STATUS_EN.get(code or "", code or ""))


_SIMPLE_ROUNDS = {"Final", "Semifinal", "Quarterfinal", "3rd place", "Grand Final",
                  "Grand Final (reset)", "WB Final", "LB Final", "Quick Match"}


def round_label(label: str | None) -> str:
    """Round labels are stored in English in the database (code compares
    against them); this translates one for display."""
    if not label:
        return ""
    if current_lang() != "vi":
        return label
    if label in _SIMPLE_ROUNDS:
        return tr(label)
    if label.startswith("Playoff "):
        return tr("Playoff · {label}", label=round_label(label[len("Playoff "):]))
    if label.startswith("WB "):
        return tr("Winners bracket · {label}", label=round_label(label[3:]))
    m = re.fullmatch(r"LB Round (\d+)", label)
    if m:
        return tr("Losers bracket · Round {n}", n=m.group(1))
    m = re.fullmatch(r"Pool (\w+) · Round (\d+)", label)
    if m:
        return tr("Pool {pool} · Round {n}", pool=m.group(1), n=m.group(2))
    m = re.fullmatch(r"Round of (\d+)", label)
    if m:
        return tr("Round of {n}", n=m.group(1))
    m = re.fullmatch(r"Round (\d+)", label)
    if m:
        return tr("Round {n}", n=m.group(1))
    return label


def ago(secs: float) -> str:
    if secs < 60:
        return tr("{n}s ago", n=int(secs))
    if secs < 3600:
        return tr("{n}m ago", n=int(secs // 60))
    if secs < 86400:
        return tr("{n}h ago", n=int(secs // 3600))
    return tr("{n}d ago", n=int(secs // 86400))
