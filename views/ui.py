"""Shared look and feel, plus the widgets every page reuses."""

from __future__ import annotations

import base64
import html
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from tourney import i18n, models
from tourney.i18n import tr
from tourney.constants import (
    CATEGORIES, FORMATS, ROLE_ADMIN, ROLE_LABEL, ROLE_REFEREE, ROLE_VIEWER, STAGE_GF,
    STAGE_LB, STAGE_PLAYOFF, STAGE_POOL, STAGE_WB, STATUS_BYE, STATUS_DONE, STATUS_LIVE,
    STATUS_PENDING, STATUS_VOID,
)

# --------------------------------------------------------------------------
# Themes
# --------------------------------------------------------------------------
# Four selectable looks, picked from the sidebar and remembered for the
# browser session (default: Stay Liquid, this event's own branding). Every
# theme shares the exact same class names, page structure, and Python
# rendering code — only a CSS variable palette, a font pairing, the page
# background, and the "wing"/"bead" decoration on the live scoreboard swap
# out underneath it.

DEFAULT_THEME = "liquid"


def _svg_uri(svg: str) -> str:
    return "data:image/svg+xml," + urllib.parse.quote(svg)


# ---- decorative "wings" flanking the live scoreboard, one per theme -------

_DROPLET_SVG = (   # Stay Liquid — a water droplet with a trail of bubbles
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 220">'
    '<path d="M30 18 C52 70 56 128 30 172 C4 128 8 70 30 18 Z" '
    'fill="#2EC4E6" opacity="0.5"/>'
    '<path d="M30 32 C46 72 48 118 30 150 C12 118 14 72 30 32 Z" '
    'fill="#146C94" opacity="0.4"/>'
    '<circle cx="21" cy="186" r="4.5" fill="#C9A227"/>'
    '<circle cx="35" cy="199" r="3" fill="#146C94"/>'
    '<circle cx="27" cy="207" r="2" fill="#2EC4E6"/>'
    '</svg>'
)

_FEATHER_SVG = (   # Tribal — a quill with alternating barbs
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 220">'
    '<path d="M30 4 C10 40 6 120 30 216 C54 120 50 40 30 4 Z" fill="#C9922E" opacity="0.55"/>'
    '<path d="M30 10 L30 210" stroke="#8B4513" stroke-width="2" fill="none"/>'
    '<path d="M30 30 L12 45 M30 30 L48 45 M30 55 L10 72 M30 55 L50 72 '
    'M30 82 L11 100 M30 82 L49 100 M30 110 L13 128 M30 110 L47 128 '
    'M30 138 L15 155 M30 138 L45 155 M30 165 L18 180 M30 165 L42 180 '
    'M30 190 L22 200 M30 190 L38 200" '
    'stroke="#B5601E" stroke-width="1.5" fill="none" stroke-linecap="round"/>'
    '</svg>'
)

_CIRCUIT_SVG = (   # Cyberpunk — a jagged neon energy trace with glowing nodes
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 220">'
    '<path d="M30 8 L30 78 L12 108 L30 108 L30 148 L48 178 L30 212" '
    'stroke="#28f6ff" stroke-width="2.5" fill="none" stroke-linecap="round" '
    'stroke-linejoin="round" opacity="0.85"/>'
    '<circle cx="30" cy="44" r="4.5" fill="#ff2fb3"/>'
    '<circle cx="12" cy="108" r="3.5" fill="#c6ff2e"/>'
    '<circle cx="48" cy="178" r="4" fill="#28f6ff"/>'
    '<circle cx="30" cy="8" r="2.5" fill="#8b5cf6"/>'
    '</svg>'
)

DROPLET_DATA_URI = _svg_uri(_DROPLET_SVG)
FEATHER_DATA_URI = _svg_uri(_FEATHER_SVG)
CIRCUIT_DATA_URI = _svg_uri(_CIRCUIT_SVG)

# The Stay Liquid background: the tournament poster's own cream silk
# texture, embedded once as a data URI, with a soft wave band washing
# across the bottom (built as an SVG so it stays crisp at any screen size).
_FABRIC_PATH = Path(__file__).parent / "assets" / "fabric_bg.jpg"
FABRIC_DATA_URI = (
    "data:image/jpeg;base64," + base64.b64encode(_FABRIC_PATH.read_bytes()).decode("ascii")
    if _FABRIC_PATH.exists() else ""
)

_WAVE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 340" '
    'preserveAspectRatio="none">'
    '<path d="M0,150 C160,196 300,96 480,132 C660,168 760,72 960,110 '
    'C1140,146 1280,88 1440,124 L1440,340 L0,340 Z" '
    'fill="#8FE0F2" fill-opacity="0.30"/>'
    '<path d="M0,196 C200,150 360,238 600,182 C800,136 980,222 1200,172 '
    'C1300,150 1380,182 1440,166 L1440,340 L0,340 Z" '
    'fill="#2EC4E6" fill-opacity="0.40"/>'
    '<path d="M0,246 C220,210 400,272 620,228 C840,184 1020,262 1240,218 '
    'C1340,198 1400,224 1440,212 L1440,340 L0,340 Z" '
    'fill="#146C94" fill-opacity="0.55"/>'
    '<path d="M0,246 C220,210 400,272 620,228 C840,184 1020,262 1240,218 '
    'C1340,198 1400,224 1440,212" fill="none" stroke="#FFFFFF" '
    'stroke-width="3.5" stroke-opacity="0.6" stroke-linecap="round"/>'
    '<circle cx="95" cy="200" r="4" fill="#FFFFFF" fill-opacity="0.65"/>'
    '<circle cx="230" cy="160" r="2.5" fill="#FFFFFF" fill-opacity="0.55"/>'
    '<circle cx="410" cy="230" r="3.5" fill="#C9A227" fill-opacity="0.55"/>'
    '<circle cx="560" cy="150" r="2" fill="#FFFFFF" fill-opacity="0.6"/>'
    '<circle cx="710" cy="200" r="3" fill="#C9A227" fill-opacity="0.5"/>'
    '<circle cx="880" cy="140" r="2.5" fill="#FFFFFF" fill-opacity="0.55"/>'
    '<circle cx="1040" cy="210" r="4" fill="#FFFFFF" fill-opacity="0.6"/>'
    '<circle cx="1190" cy="160" r="2.5" fill="#C9A227" fill-opacity="0.5"/>'
    '<circle cx="1340" cy="195" r="3" fill="#FFFFFF" fill-opacity="0.55"/>'
    '</svg>'
)
WAVE_DATA_URI = _svg_uri(_WAVE_SVG)

_LIQUID_BG = f"""
  background-color: var(--cream);
  background-image:
    radial-gradient(ellipse 70% 45% at 15% 0%, rgba(255,255,255,.55), transparent 60%),
    radial-gradient(ellipse 60% 40% at 90% 100%, rgba(20,108,148,.10), transparent 60%),
    url("{WAVE_DATA_URI}"),
    url("{FABRIC_DATA_URI}");
  background-position: 0 0, 0 0, center bottom, center top;
  background-repeat: no-repeat, no-repeat, no-repeat, no-repeat;
  background-size: auto, auto, 100% 300px, cover;
  background-attachment: scroll, scroll, fixed, fixed;
"""

_TRIBAL_BG = """
  background-color: var(--cream);
  background-image:
    radial-gradient(ellipse 70% 45% at 15% 0%, rgba(255,255,255,.75), transparent 60%),
    radial-gradient(ellipse 60% 40% at 90% 100%, rgba(201,146,46,.10), transparent 60%);
"""

_CYBERPUNK_BG = """
  background-color: var(--cream);
  background-image:
    linear-gradient(rgba(139,92,246,.10) 1px, transparent 1px),
    linear-gradient(90deg, rgba(139,92,246,.10) 1px, transparent 1px);
  background-size: 42px 42px;
"""

# ---- the border strip along the top/bottom of the live scoreboard --------
_LIQUID_STRIP = (
    'background-image: radial-gradient(circle at 8px 5px, var(--amber) 3px, transparent 3.5px);'
    'background-size: 16px 16px; background-position: 0 0; background-repeat: repeat-x;'
)
_TRIBAL_STRIP = (
    'background-image: linear-gradient(135deg, var(--terracotta) 25%, transparent 25.5%), '
    'linear-gradient(225deg, var(--terracotta) 25%, transparent 25.5%);'
    'background-size: 16px 16px; background-position: 0 0; background-repeat: repeat-x;'
)
_CYBERPUNK_STRIP = (
    'background-image: repeating-linear-gradient(90deg, var(--amber) 0 8px, transparent 8px 16px);'
    'background-size: auto; background-position: 0 0; background-repeat: repeat-x; '
    'opacity: .8;'
)

_MINIMAL_BG = "background-color: var(--cream);"
_MINIMAL_STRIP = "background-color: var(--line); background-image: none;"
_BLANK_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 220"></svg>'
BLANK_DATA_URI = _svg_uri(_BLANK_SVG)

THEMES = {
    "liquid": {
        "label": "Stay Liquid — ocean & gold",
        "font_import_url": "family=Be+Vietnam+Pro:wght@400;500;600;700;800;900",
        "font_body": "'Be Vietnam Pro', system-ui, sans-serif",
        "font_display": "'Be Vietnam Pro', system-ui, sans-serif",
        "vars": {
            "cream": "#F4F1EA", "parchment": "#FFFFFF", "panel2": "#E8F1F6", "line": "#CBD9E3",
            "terracotta": "#146C94", "rust": "#0B3B57", "amber": "#2EC4E6", "gold": "#C9A227",
            "olive": "#2A8C82", "ink": "#0B2B3D", "mute": "#5C7A8C",
            "bead-radius": "50%", "bead-rotate": "0deg",
        },
        "background": _LIQUID_BG,
        "wing_uri": DROPLET_DATA_URI,
        "border_strip": _LIQUID_STRIP,
        "board_shadow": "0 2px 10px rgba(20,108,148,.15)",
    },
    "tribal": {
        "label": "Tribal — ivory & terracotta",
        "font_import_url": "family=Cinzel:wght@600;700;800&family=Karla:wght@400;500;600;700;800",
        "font_body": "'Karla', system-ui, sans-serif",
        "font_display": "'Cinzel', serif",
        "vars": {
            "cream": "#F3EBDF", "parchment": "#FBF6EC", "panel2": "#ECE0CB", "line": "#D9C7A6",
            "terracotta": "#B5601E", "rust": "#8B4513", "amber": "#C9922E", "gold": "#B8860B",
            "olive": "#6B6B3F", "ink": "#2B1B0E", "mute": "#8A7457",
            "bead-radius": "0%", "bead-rotate": "45deg",
        },
        "background": _TRIBAL_BG,
        "wing_uri": FEATHER_DATA_URI,
        "border_strip": _TRIBAL_STRIP,
        "board_shadow": "0 2px 10px rgba(139,69,19,.13)",
    },
    "cyberpunk": {
        "label": "Cyberpunk — neon HUD",
        "font_import_url": "family=Orbitron:wght@600;700;800;900&family=Rajdhani:wght@400;500;600;700"
                           "&family=Share+Tech+Mono",
        "font_body": "'Rajdhani', system-ui, sans-serif",
        "font_display": "'Orbitron', system-ui, sans-serif",
        "vars": {
            "cream": "#07020f", "parchment": "#0f0a24", "panel2": "#150d30", "line": "#2c2358",
            "terracotta": "#28f6ff", "rust": "#8b5cf6", "amber": "#ff2fb3", "gold": "#c6ff2e",
            "olive": "#8f89bd", "ink": "#eae6ff", "mute": "#8f89bd",
            "bead-radius": "2px", "bead-rotate": "0deg",
        },
        "background": _CYBERPUNK_BG,
        "wing_uri": CIRCUIT_DATA_URI,
        "border_strip": _CYBERPUNK_STRIP,
        "board_shadow": "0 0 18px rgba(40,246,255,.25)",
    },
    "minimal": {
        "label": "Minimal — clean & simple",
        "font_import_url": "family=Be+Vietnam+Pro:wght@400;500;600;700;800",
        "font_body": "'Be Vietnam Pro', system-ui, sans-serif",
        "font_display": "'Be Vietnam Pro', system-ui, sans-serif",
        "vars": {
            "cream": "#F7F7F5", "parchment": "#FFFFFF", "panel2": "#F0F0EE", "line": "#E2E2DE",
            "terracotta": "#2563EB", "rust": "#1D4ED8", "amber": "#64748B", "gold": "#FFFFFF",
            "olive": "#475569", "ink": "#111827", "mute": "#6B7280",
            "bead-radius": "50%", "bead-rotate": "0deg",
        },
        "background": _MINIMAL_BG,
        "wing_uri": BLANK_DATA_URI,
        "border_strip": _MINIMAL_STRIP,
        "board_shadow": "0 1px 3px rgba(17,24,39,.08)",
    },
}


def theme_options() -> dict[str, str]:
    """key -> label, in display order, for the sidebar picker."""
    return {k: tr(v["label"]) for k, v in THEMES.items()}


def current_theme_key() -> str:
    return st.session_state.get("ui_theme", DEFAULT_THEME)


def set_theme(key: str):
    if key in THEMES:
        st.session_state["ui_theme"] = key


# --------------------------------------------------------------------------
# The shared CSS skeleton — identical for every theme. Colors are all
# `var(--name)`, so the only thing that differs page to page is which
# `:root` block, background, fonts, and wing/border decoration got
# substituted in by `inject_css()` below. Where a theme needs a tinted
# translucent color (a soft highlight, a hover glow) this uses `color-mix()`
# against the live palette instead of a hardcoded rgba(), so it re-tints
# itself automatically for whichever theme is active.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?__FONT_IMPORT_URL__&display=swap');

:root {
  --cream:      __cream__;
  --parchment:  __parchment__;
  --panel2:     __panel2__;
  --line:       __line__;
  --terracotta: __terracotta__;
  --rust:       __rust__;
  --amber:      __amber__;
  --gold:       __gold__;
  --olive:      __olive__;
  --ink:        __ink__;
  --mute:       __mute__;
  --bead-radius: __bead-radius__;
  --bead-rotate: __bead-rotate__;
  --font-body: __FONT_BODY__;
  --font-display: __FONT_DISPLAY__;
}

html, body, [class*="css"], .stApp { font-family: var(--font-body); }
.stApp {
  __BACKGROUND__
}
.stApp, .stApp p, .stApp span, .stApp label, .stApp li { color: var(--ink); }
.stApp .stMarkdown, .stApp .stCaption, .stApp small { color: var(--mute); }

h1, h2, h3, h4 { font-family: var(--font-display); letter-spacing: .01em; color: var(--ink); }
h1 { font-weight: 700; }

/* --- page masthead ---------------------------------------------------- */
.pk-head { border-bottom: 2px solid var(--rust); padding-bottom: .5rem; margin-bottom: 1.1rem; }
.pk-head .eyebrow {
  font-family: var(--font-body); font-weight: 700; font-size: .68rem; letter-spacing: .22em;
  text-transform: uppercase; color: var(--terracotta);
}
.pk-head .title { font-family: var(--font-display); font-weight: 700; font-size: 1.7rem;
  line-height: 1.25; color: var(--ink); margin-top: .2rem; }

/* --- brand mark in the sidebar ------------------------------------------ */
.pk-brand { font-family: var(--font-display); font-weight: 700; font-size: 1.2rem;
  line-height: 1.3; color: var(--ink); }
.pk-brand .accent { color: var(--terracotta); }
.pk-brand-sub { font-family: var(--font-body); font-weight: 700; font-size: .62rem;
  letter-spacing: .2em; text-transform: uppercase; color: var(--mute); margin-top: .25rem; }

/* --- corner-bracket motif, used on ordinary cards ----------------------- */
.pk-bracketed { position: relative; }
.pk-bracketed::before, .pk-bracketed::after {
  content: ""; position: absolute; width: 10px; height: 10px; pointer-events: none;
}
.pk-bracketed::before { top: -1px; left: -1px; border-top: 2px solid currentColor; border-left: 2px solid currentColor; }
.pk-bracketed::after  { bottom: -1px; right: -1px; border-bottom: 2px solid currentColor; border-right: 2px solid currentColor; }

/* --- the scoreboard strip: this app's signature element ----------------- */
.pk-board {
  background: var(--parchment); color: var(--ink); border-radius: 4px; padding: 1.15rem 2.5rem;
  margin: 1rem 0 .9rem; position: relative;
  border-left: 3px solid var(--terracotta); border-right: 3px solid var(--terracotta);
  box-shadow: __BOARD_SHADOW__;
}
.pk-board::before, .pk-board::after {
  content: ""; position: absolute; left: -3px; right: -3px; height: 9px;
  __BORDER_STRIP__
}
.pk-board::before { top: -9px; }
.pk-board::after { bottom: -9px; }
.pk-board .bead {
  position: absolute; width: 9px; height: 9px; border-radius: var(--bead-radius);
  transform: rotate(var(--bead-rotate)); background: var(--gold);
  border: 1.5px solid var(--rust); z-index: 2;
}
.pk-board .bead.tl { top: -13px; left: -6px; }
.pk-board .bead.tr { top: -13px; right: -6px; }
.pk-board .bead.bl { bottom: -13px; left: -6px; }
.pk-board .bead.br { bottom: -13px; right: -6px; }
.pk-board .meta {
  font-family: var(--font-body); font-weight: 700; font-size: .66rem; letter-spacing: .16em;
  text-transform: uppercase; color: var(--mute); display: flex; gap: .8rem; align-items: center;
  margin-bottom: .55rem; flex-wrap: wrap;
}
.pk-board .history {
  font-family: var(--font-body); font-size: .74rem; color: var(--mute);
  margin-bottom: .6rem; letter-spacing: .01em;
}
.pk-board .scoreline { display: flex; flex-direction: column; gap: .15rem; }
.pk-board .srow {
  display: flex; justify-content: space-between; align-items: center;
  gap: 1rem; padding: .22rem 0;
}
.pk-board .srow .sname {
  font-family: var(--font-body); font-weight: 700; font-size: 1.08rem; color: var(--ink);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.pk-board .srow .snum {
  font-family: var(--font-display); font-weight: 800; font-size: 2.5rem; line-height: 1;
  color: var(--terracotta); font-variant-numeric: tabular-nums; min-width: 1.4ch; text-align: right;
}
.pk-board .srow.leading .sname { color: var(--rust); }
.pk-board .srow.leading .snum { color: var(--rust); }

/* --- grid of simultaneous live matches, one card per court ------------- */
.pk-live-grid {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px; margin: .8rem 0 1.4rem;
}
.pk-live-grid .pk-board { margin: 0; height: 100%; }
@media (max-width: 720px) {
  .pk-live-grid { grid-template-columns: 1fr; }
}

/* --- "wings" flanking the live scoreboard ------------------------------- */
.pk-board .wing {
  position: absolute; top: 50%; transform: translateY(-50%); width: 22px; height: 96px;
  background-image: url("__WING_URI__"); background-repeat: no-repeat;
  background-position: center; background-size: contain; opacity: .8; pointer-events: none;
}
.pk-board .wing.left { left: 8px; }
.pk-board .wing.right { right: 8px; transform: translateY(-50%) scaleX(-1); }

/* --- mobile: give content room back from decoration and oversized type -- */
@media (max-width: 600px) {
  .pk-head .title { font-size: 1.35rem; }
  .pk-board { padding-left: 1.7rem; padding-right: 1.7rem; }
  .pk-board .wing { width: 14px; height: 64px; opacity: .6; }
  .pk-board .wing.left { left: 2px; }
  .pk-board .wing.right { right: 2px; }
  .pk-board .srow .snum { font-size: 2rem; }
  .pk-board .meta { gap: .5rem; font-size: .62rem; }
  .pk-scorenum { font-size: 2.3rem; }
}

.pk-srv { display:inline-block; width:.62em; height:.62em; border-radius:50%; background:#d7f23a;
  border:2px solid #7d9416; margin-right:.45rem; vertical-align: .05em; }
.pk-live-dot {
  width: 9px; height: 9px; border-radius: 50%; background: var(--terracotta);
  display: inline-block; box-shadow: 0 0 0 0 color-mix(in srgb, var(--terracotta) 65%, transparent);
  animation: pk-pulse 1.7s infinite;
}
@keyframes pk-pulse {
  0%   { box-shadow: 0 0 0 0 color-mix(in srgb, var(--terracotta) 55%, transparent); }
  70%  { box-shadow: 0 0 0 9px color-mix(in srgb, var(--terracotta) 0%, transparent); }
  100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--terracotta) 0%, transparent); }
}
@media (prefers-reduced-motion: reduce) { .pk-srv { display:inline-block; width:.62em; height:.62em; border-radius:50%; background:#d7f23a;
  border:2px solid #7d9416; margin-right:.45rem; vertical-align: .05em; }
.pk-live-dot { animation: none; } }

/* --- the point-by-point scoring desk ------------------------------------ */
.pk-scoreup {
  font-family: var(--font-body); font-weight: 700; font-size: .78rem; letter-spacing: .1em;
  text-transform: uppercase; color: var(--mute); text-align: center; margin-bottom: .1rem;
}
.pk-scorenum {
  font-family: var(--font-display); font-weight: 800; font-size: 3rem; line-height: 1.1;
  text-align: center; color: var(--terracotta);
  font-variant-numeric: tabular-nums; margin-bottom: .35rem;
}

/* --- quieter card for finished / upcoming ------------------------------- */
.pk-card {
  background: var(--parchment); border: 1px solid var(--line); border-left: 3px solid var(--line);
  border-radius: 6px; padding: .7rem .85rem; margin-bottom: .5rem;
}
.pk-card.done { border-left-color: var(--olive); }
.pk-card.next { border-left-color: var(--amber); }
.pk-card .meta { font-family: var(--font-body); font-weight: 700; font-size: .64rem; letter-spacing: .14em;
  text-transform: uppercase; color: var(--mute); margin-bottom: .35rem; }
.pk-card .row { display: flex; justify-content: space-between; gap: 1rem; padding: .1rem 0; }
.pk-card .side { font-size: .95rem; color: var(--ink); }
.pk-card .side.win { font-weight: 700; color: var(--terracotta); }
.pk-card .side.loss { color: var(--mute); }
.pk-card .pts { font-family: var(--font-body); font-variant-numeric: tabular-nums;
  color: var(--ink); font-size: .9rem; white-space: nowrap; font-weight: 600; }

/* --- tags ---------------------------------------------------------------- */
.pk-tag {
  display: inline-block; font-family: var(--font-body); font-weight: 700; font-size: .62rem;
  letter-spacing: .1em; text-transform: uppercase; padding: .16rem .45rem;
  border-radius: 4px; background: color-mix(in srgb, var(--terracotta) 10%, transparent);
  color: var(--terracotta);
  border: 1px solid color-mix(in srgb, var(--terracotta) 35%, transparent); margin-right: .3rem;
}
.pk-tag.warn { background: color-mix(in srgb, var(--rust) 12%, transparent); color: var(--rust);
  border-color: color-mix(in srgb, var(--rust) 35%, transparent); }
.pk-tag.mute { background: var(--panel2); color: var(--mute); border-color: var(--line); }

/* --- bracket -------------------------------------------------------------- */
.pk-bracket { display: flex; gap: 14px; overflow-x: auto; padding: .4rem .1rem 1rem; }
.pk-round { min-width: 208px; display: flex; flex-direction: column; justify-content: space-around; gap: 10px; }
.pk-round .rlabel {
  font-family: var(--font-body); font-weight: 700; font-size: .62rem; letter-spacing: .15em;
  text-transform: uppercase; color: var(--olive); border-bottom: 1px solid var(--line);
  padding-bottom: .3rem; margin-bottom: .2rem;
}
.pk-node { background: var(--parchment); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
.pk-node.live { border-color: var(--terracotta);
  box-shadow: inset 3px 0 0 var(--terracotta), 0 0 12px color-mix(in srgb, var(--terracotta) 15%, transparent); }
.pk-node .n-row {
  display: flex; justify-content: space-between; align-items: center; gap: .5rem;
  padding: .32rem .5rem; font-size: .83rem; border-bottom: 1px solid var(--panel2);
  color: var(--ink);
}
.pk-node .n-row:last-child { border-bottom: none; }
.pk-node .n-row.win { font-weight: 700; background: color-mix(in srgb, var(--terracotta) 8%, transparent); color: var(--terracotta); }
.pk-node .n-row.tbd { color: var(--mute); font-style: italic; }
.pk-node .n-pts { font-family: var(--font-body); font-variant-numeric: tabular-nums; font-size: .78rem; font-weight: 600; }
.pk-node .n-cap {
  font-family: var(--font-body); font-weight: 700; font-size: .58rem; letter-spacing: .1em;
  text-transform: uppercase; color: var(--terracotta); padding: .18rem .5rem; background: var(--panel2);
}

/* --- misc ------------------------------------------------------------------ */
.pk-empty { border: 1px dashed var(--line); border-radius: 8px; padding: 1.4rem;
  text-align: center; color: var(--mute); background: var(--parchment); }
.pk-activity { font-family: var(--font-body); font-size: .68rem; color: var(--mute);
  line-height: 1.7; }

/* --- Streamlit native widget re-skin ---------------------------------------- */
div[data-testid="stMetricValue"] { font-family: var(--font-display); font-weight: 700; color: var(--terracotta); }
div[data-testid="stMetricLabel"] { font-family: var(--font-body); color: var(--mute); }
section[data-testid="stSidebar"] { background: var(--panel2); border-right: 1px solid var(--line); }
header[data-testid="stHeader"] { background: var(--cream); }
div[data-testid="stToolbar"] { color: var(--ink); }
div[data-testid="stDecoration"] { background: var(--terracotta); }
section[data-testid="stSidebar"] * { color: var(--ink); }

.stButton button, .stFormSubmitButton button, .stDownloadButton button {
  border-radius: 6px; font-weight: 700; font-family: var(--font-body);
  letter-spacing: .03em; text-transform: uppercase; font-size: .85rem;
  background: color-mix(in srgb, var(--terracotta) 8%, transparent); color: var(--terracotta);
  border: 1px solid color-mix(in srgb, var(--terracotta) 50%, transparent);
  transition: transform .15s ease, box-shadow .2s ease, background-color .2s ease;
}
.stButton button:hover, .stFormSubmitButton button:hover, .stDownloadButton button:hover {
  background: color-mix(in srgb, var(--terracotta) 16%, transparent);
  box-shadow: 0 2px 10px color-mix(in srgb, var(--terracotta) 30%, transparent);
  border-color: var(--terracotta); color: var(--rust);
}
.stButton button:active, .stFormSubmitButton button:active, .stDownloadButton button:active {
  transform: translateY(1px) scale(.99);
}
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
  background: var(--terracotta); color: var(--parchment); border-color: var(--terracotta);
}
.stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover {
  background: var(--rust); box-shadow: 0 2px 14px color-mix(in srgb, var(--rust) 40%, transparent);
}
.stButton button:focus-visible, .stFormSubmitButton button:focus-visible,
.stDownloadButton button:focus-visible, a:focus-visible, input:focus-visible,
[tabindex]:focus-visible, .stSelectbox div[data-baseweb="select"]:focus-within {
  outline: 2px solid var(--terracotta) !important; outline-offset: 2px;
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--terracotta) 18%, transparent) !important;
}

/* --- form controls: every part of every widget takes the theme's colours,
   whatever light/dark mode the device is in -------------------------------- */
div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="textarea"],
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
  background: var(--parchment) !important; border-color: var(--line) !important;
}
.stApp input, .stApp textarea, section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea {
  background: var(--parchment) !important; color: var(--ink) !important;
  -webkit-text-fill-color: var(--ink) !important; caret-color: var(--terracotta);
}
.stApp input::placeholder, .stApp textarea::placeholder,
section[data-testid="stSidebar"] input::placeholder {
  color: var(--mute) !important; -webkit-text-fill-color: var(--mute) !important; opacity: .75;
}
div[data-baseweb="select"] *, div[data-baseweb="select"] input {
  color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important;
}
div[data-baseweb="select"] svg, div[data-baseweb="input"] svg { fill: var(--mute) !important; color: var(--mute) !important; }
/* password "eye", number +/- steppers, clear buttons */
div[data-baseweb="input"] button {
  background: var(--panel2) !important; color: var(--ink) !important; border-color: var(--line) !important;
}
div[data-baseweb="input"] button svg { fill: var(--ink) !important; }
/* drop-down menus open in a portal outside the page, so target them directly */
div[data-baseweb="popover"] > div, div[data-baseweb="popover"] ul, div[data-baseweb="menu"],
ul[role="listbox"], div[data-testid="stSelectboxVirtualDropdown"] {
  background: var(--parchment) !important; color: var(--ink) !important; border-color: var(--line) !important;
}
li[role="option"], li[role="option"] *, ul[role="listbox"] li { color: var(--ink) !important; background: transparent; }
li[role="option"]:hover, li[role="option"][aria-selected="true"] {
  background: color-mix(in srgb, var(--terracotta) 14%, var(--parchment)) !important;
}
span[data-baseweb="tag"] {
  background: color-mix(in srgb, var(--terracotta) 16%, var(--parchment)) !important;
  color: var(--ink) !important;
}
span[data-baseweb="tag"] * { color: var(--ink) !important; fill: var(--ink) !important; }
div[data-baseweb="calendar"], div[data-baseweb="calendar"] * {
  background-color: var(--parchment); color: var(--ink) !important;
}
/* inline code chips (e.g. the default passcodes in the sidebar) */
.stApp code, section[data-testid="stSidebar"] code {
  background: color-mix(in srgb, var(--terracotta) 12%, var(--parchment)) !important;
  color: var(--rust) !important; border-radius: 4px; padding: .05rem .3rem;
}
/* alerts and expanders */
/* Alerts mix their meaning colour into the theme's panel colour, so text in
   the theme's ink colour stays readable in light and dark themes alike. */
div[data-testid="stAlertContainer"] {
  background: color-mix(in srgb, #2b7bd6 14%, var(--parchment)) !important;
  border: 1px solid color-mix(in srgb, #2b7bd6 35%, transparent);
}
div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {
  background: color-mix(in srgb, #1e9e55 16%, var(--parchment)) !important;
  border-color: color-mix(in srgb, #1e9e55 40%, transparent); }
div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {
  background: color-mix(in srgb, #e3a008 20%, var(--parchment)) !important;
  border-color: color-mix(in srgb, #e3a008 45%, transparent); }
div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {
  background: color-mix(in srgb, #d93025 16%, var(--parchment)) !important;
  border-color: color-mix(in srgb, #d93025 45%, transparent); }
div[data-testid="stAlertContainer"] * { color: var(--ink) !important; }
details summary, details summary * { color: var(--ink) !important; }
label, label * , div[data-testid="stWidgetLabel"] * { color: var(--ink) !important; }
div[data-testid="stCheckbox"] span, div[data-testid="stRadio"] span { color: var(--ink); }
div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] { font-family: var(--font-body); font-weight: 700; font-size: .78rem;
  letter-spacing: .08em; text-transform: uppercase; color: var(--mute); }
.stTabs [aria-selected="true"] { color: var(--terracotta) !important; }
div[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 8px; background: var(--parchment); }
hr { border-color: var(--line) !important; }
div[data-testid="InputInstructions"] { display: none !important; }

/* --- Streamlit 1.6x widgets (react-aria based). Every part is given the
   theme's colours so nothing depends on the device's light/dark mode or on
   .streamlit/config.toml being found. ------------------------------------- */
/* select boxes & multiselects: the field, the arrow button, the tags */
div[data-testid="stSelectbox"] [role="group"], div[data-testid="stMultiSelect"] [role="group"]:not([aria-label]) {
  background: var(--parchment) !important; border-color: var(--line) !important; }
div[data-testid="stSelectbox"] [role="group"] button,
div[data-testid="stMultiSelect"] [role="group"] > button {
  background: transparent !important; color: var(--mute) !important; border: none !important; }
div[data-testid="stSelectbox"] input, div[data-testid="stMultiSelect"] input {
  background: transparent !important; color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important; }
div[data-testid="stMultiSelect"] [data-tag] {
  background: color-mix(in srgb, var(--terracotta) 16%, var(--parchment)) !important; color: var(--ink) !important; }
div[data-testid="stMultiSelect"] [data-tag] * { color: var(--ink) !important; }
/* the open drop-down list */
div[data-testid="stSelectboxVirtualDropdown"], [role="listbox"] {
  background: var(--parchment) !important; border-color: var(--line) !important; }
[role="listbox"] [role="option"], [role="listbox"] [role="option"] * {
  color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important; }
[role="listbox"] [role="option"][aria-selected="true"], [role="listbox"] [role="option"]:hover,
[role="listbox"] [role="option"][data-focused="true"] {
  background: color-mix(in srgb, var(--terracotta) 14%, var(--parchment)) !important; }
/* number inputs: field + steppers */
div[data-testid="stNumberInputContainer"] { background: var(--parchment) !important; border-color: var(--line) !important; }
div[data-testid="stNumberInputContainer"] button {
  background: var(--panel2) !important; color: var(--ink) !important; border-color: var(--line) !important; }
div[data-testid="stNumberInputContainer"] button svg { fill: var(--ink) !important; color: var(--ink) !important; }
/* date inputs */
div[data-testid="stDateInputField"], div[data-testid="stDateInputField"] [role="group"] {
  background: var(--parchment) !important; border-color: var(--line) !important; }
div[data-testid="stDateInputField"] [role="spinbutton"], div[data-testid="stDateInputField"] span {
  color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important; }
/* the "?" help icons: an outline, never a filled dot */
span[data-testid="stTooltipIcon"] button, span[data-testid="stTooltipHoverTarget"] button {
  background: transparent !important; border: none !important; box-shadow: none !important; }
span[data-testid="stTooltipIcon"] svg {
  fill: none !important; stroke: var(--mute) !important; color: var(--mute) !important; }
/* radio buttons */
label[data-testid="stRadioOption"] > div > div:first-child {
  background: var(--parchment) !important; border: 2px solid var(--mute) !important; box-shadow: none !important; }
label[data-testid="stRadioOption"] > div > div:first-child > div { background: transparent !important; }
label[data-testid="stRadioOption"][data-selected="true"] > div > div:first-child {
  background: var(--terracotta) !important; border-color: var(--terracotta) !important;
  box-shadow: inset 0 0 0 3px var(--parchment) !important; }
/* checkboxes */
div[data-testid="stCheckbox"] label:not(:has([role="switch"])) > div:first-of-type {
  background: var(--parchment) !important; border: 2px solid var(--mute) !important; }
div[data-testid="stCheckbox"][data-selected="true"] label:not(:has([role="switch"])) > div:first-of-type {
  background: var(--terracotta) !important; border-color: var(--terracotta) !important; }
div[data-testid="stCheckbox"] label:not(:has([role="switch"])) > div:first-of-type svg { stroke: var(--parchment) !important; }
/* toggles */
div[data-testid="stCheckbox"] label:has([role="switch"]) > div:first-of-type {
  background: var(--line) !important; }
div[data-testid="stCheckbox"][data-selected="true"] label:has([role="switch"]) > div:first-of-type {
  background: color-mix(in srgb, var(--terracotta) 60%, var(--parchment)) !important; }
div[data-testid="stCheckbox"] label:has([role="switch"]) > div:first-of-type > div {
  background: var(--parchment) !important; box-shadow: 0 1px 3px rgba(0,0,0,.3) !important; }
div[data-testid="stCheckbox"][data-selected="true"] label:has([role="switch"]) > div:first-of-type > div {
  background: var(--terracotta) !important; }
/* button text: Streamlit wraps labels in <p>, which our page-wide text colour would hit */
.stButton button p, .stFormSubmitButton button p, .stDownloadButton button p { color: inherit !important; }
.stButton button[kind="primary"] p, .stFormSubmitButton button[kind="primary"] p {
  color: var(--parchment) !important; }
/* Streamlit's own developer toolbar is English-only — hide it even without config.toml */
div[data-testid="stToolbarActions"], .stAppDeployButton, div[data-testid="stAppDeployButton"] {
  display: none !important; }
/* progress bar track/fill */
div[data-testid="stProgress"] div[role="progressbar"] > div { background: var(--line) !important; }
div[data-testid="stProgress"] div[role="progressbar"] > div > div { background: var(--terracotta) !important; }
</style>
"""


def theme_color(name: str) -> str:
    """The active theme's hex value for a named role (terracotta, olive,
    gold, etc) — for call sites that need a real color string rather than a
    CSS var(), such as the sortable-widget styling below."""
    return THEMES[current_theme_key()]["vars"][name]


def sortable_css(accent: str | None = None) -> str:
    """CSS for streamlit-sortables drag-and-drop widgets, themed to match the
    rest of the desk. `accent` tints headers, hover glow and item borders —
    defaults to the active theme's primary accent if not given."""
    t = THEMES[current_theme_key()]
    accent = accent or t["vars"]["terracotta"]
    parchment, line, panel2, ink = (t["vars"]["parchment"], t["vars"]["line"],
                                    t["vars"]["panel2"], t["vars"]["ink"])
    return f"""
    .sortable-component {{ background: transparent; }}
    .sortable-container {{
      background: {parchment}; border: 1px solid {line}; border-radius: 10px;
      padding: 10px; min-height: 64px;
    }}
    .sortable-container-header {{
      font-family: {t["font_body"]}; font-weight: 700; font-size: 11px; letter-spacing: .14em;
      text-transform: uppercase; color: {accent}; padding-bottom: 6px;
      border-bottom: 1px solid {line}; margin-bottom: 8px;
    }}
    .sortable-item {{
      background: {panel2}; border: 1px solid {line}; color: {ink};
      border-radius: 6px; padding: 7px 11px; font-family: {t["font_body"]};
      font-weight: 600; font-size: 14px; cursor: grab; transition: all .15s ease;
    }}
    .sortable-item:hover {{ border-color: {accent}; box-shadow: 0 2px 8px {accent}55; }}
    """


def inject_css():
    t = THEMES[current_theme_key()]
    css = CSS
    css = css.replace("__FONT_IMPORT_URL__", t["font_import_url"])
    css = css.replace("__FONT_BODY__", t["font_body"])
    css = css.replace("__FONT_DISPLAY__", t["font_display"])
    css = css.replace("__BACKGROUND__", t["background"])
    css = css.replace("__BORDER_STRIP__", t["border_strip"])
    css = css.replace("__BOARD_SHADOW__", t["board_shadow"])
    css = css.replace("__WING_URI__", t["wing_uri"])
    for name, value in t["vars"].items():
        css = css.replace(f"__{name}__", value)
    st.markdown(css, unsafe_allow_html=True)

def masthead(eyebrow: str, title: str):
    st.markdown(
        f'<div class="pk-head"><div class="eyebrow">{html.escape(eyebrow)}</div>'
        f'<div class="title">{html.escape(title)}</div></div>',
        unsafe_allow_html=True)


def empty_state(message: str):
    st.markdown(f'<div class="pk-empty">{html.escape(message)}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Session helpers
# --------------------------------------------------------------------------

def admin_name() -> str | None:
    """Display name of whoever is signed in (admin or referee)."""
    return st.session_state.get("admin_name")


def role() -> str:
    return st.session_state.get("role") or ROLE_VIEWER


def role_label() -> str:
    key = {ROLE_ADMIN: "role.admin", ROLE_REFEREE: "role.referee", ROLE_VIEWER: "role.viewer"}.get(role())
    return i18n.t(key) if key else ROLE_LABEL.get(role(), "Viewer")


def is_admin() -> bool:
    return role() == ROLE_ADMIN


def is_referee() -> bool:
    return role() == ROLE_REFEREE


def can_score() -> bool:
    """Admins and referees can both use the scoring desk."""
    return role() in (ROLE_ADMIN, ROLE_REFEREE)


def require_admin(action=None) -> bool:
    action = action or tr("make changes")
    if is_admin():
        return True
    st.info(tr("Sign in as an admin in the sidebar to {action}. You can still read everything here.",
               action=action))
    return False


def require_scorer(action=None) -> bool:
    action = action or tr("enter scores")
    if can_score():
        return True
    st.info(tr("Sign in as an admin or referee in the sidebar to {action}. "
               "You can still read everything here.", action=action))
    return False


def current_tournament_id() -> int | None:
    return st.session_state.get("tournament_id")


def need_tournament() -> dict | None:
    tid = current_tournament_id()
    if not tid:
        empty_state(tr("Pick a tournament in the sidebar, or create one on the Setup page."))
        return None
    t = models.get_tournament(tid)
    if not t:
        st.session_state.pop("tournament_id", None)
        empty_state(tr("That tournament no longer exists."))
        return None
    return t


def event_picker(tournament_id, key, label=None, include_all=False):
    label = label or tr("Event")
    events = models.list_events(tournament_id)
    if not events:
        return None
    opts = [e["id"] for e in events]
    labels = {e["id"]: f"{i18n.cat(e['category'])} · {i18n.fmt(e['format'])}" for e in events}
    if include_all:
        opts = [0] + opts
        labels[0] = tr("All events")
    return st.selectbox(label, opts, format_func=lambda i: labels[i], key=key)


# --------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------

def score_string(games, side="a") -> str:
    if not games:
        return ""
    return "  ".join(f"{g['score_a']}–{g['score_b']}" if side == "a"
                     else f"{g['score_b']}–{g['score_a']}" for g in games)


def match_title(m, ev=None) -> str:
    bits = []
    if ev:
        bits.append(i18n.category_label(ev["category"], CATEGORIES[ev["category"]]))
    if m.get("stage") in (STAGE_WB, STAGE_LB, STAGE_GF, STAGE_PLAYOFF, STAGE_POOL) and m.get("pool") \
            and not (m.get("round_label") or "").startswith("Pool "):
        bits.append(tr("Pool {p}", p=m["pool"]))
    bits.append(i18n.round_label(m.get("round_label")) or tr("Round {n}", n=m["round_no"]))
    bits.append(tr("M{n}", n=m["match_no"]))
    return " · ".join(bits)


def ago(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        t = datetime.fromisoformat(iso)
    except ValueError:
        return ""
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return i18n.ago((datetime.now(timezone.utc) - t).total_seconds())


# --------------------------------------------------------------------------
# Match rendering
# --------------------------------------------------------------------------

def _name(entry_id, emap) -> str:
    if entry_id is None:
        return tr("TBD")
    e = emap.get(entry_id)
    return e["name"] if e else tr("TBD")


def live_match_html(m, emap, games, ev=None) -> str:
    """One live-match card as an HTML string — completed games recapped in
    a small line, the score that matters (this game, right now) shown big
    and unambiguous, with the side currently ahead picked out in color."""
    a = html.escape(_name(m["entry_a_id"], emap))
    b = html.escape(_name(m["entry_b_id"], emap))
    cur_a, cur_b = int(m.get("cur_a", 0) or 0), int(m.get("cur_b", 0) or 0)
    court = html.escape(m["court"] or tr("court TBD"))
    meta = (f'<span class="pk-live-dot"></span><span>{tr("Live")}</span>'
            f'<span>{html.escape(match_title(m, ev))}</span><span>{court}</span>')
    beads = ('<span class="bead tl"></span><span class="bead tr"></span>'
            '<span class="bead bl"></span><span class="bead br"></span>')
    wings = '<span class="wing left"></span><span class="wing right"></span>'
    history = ""
    if games:
        recap = "  ·  ".join(tr("G{n}", n=g["game_no"]) + f" {g['score_a']}–{g['score_b']}" for g in games)
        history = f'<div class="history">{html.escape(recap)}</div>'
    lead_a = " leading" if cur_a > cur_b else ""
    lead_b = " leading" if cur_b > cur_a else ""
    # Who's serving, and the referee's call ("4 – 2 – 1"), straight from the rules.
    state = models.serve_state(m) if m.get("serve_state") else None
    srv_a = srv_b = ""
    if state and not state.get("game_over"):
        from tourney import rules
        dot = '<span class="pk-srv" title="serving"></span>'
        srv_a, srv_b = (dot, "") if state["serving"] == "a" else ("", dot)
        call = rules.score_call(state, (cur_a, cur_b))
        meta += f'<span>{html.escape(tr("Call {call}", call=call))}</span>'
    return (
        f'<div class="pk-board">{beads}{wings}<div class="meta">{meta}</div>{history}'
        f'<div class="scoreline">'
        f'<div class="srow{lead_a}"><span class="sname">{srv_a}{a}</span><span class="snum">{cur_a}</span></div>'
        f'<div class="srow{lead_b}"><span class="sname">{srv_b}{b}</span><span class="snum">{cur_b}</span></div>'
        f'</div></div>')


def render_live_match(m, emap, games, ev=None):
    st.markdown(live_match_html(m, emap, games, ev), unsafe_allow_html=True)


def render_live_grid(matches, emap, games_by_match, ev_by_id):
    """All simultaneous live matches — one card per court — laid out in a
    responsive grid (4 across on a wide screen, wrapping on a narrow one)
    so a room running several courts at once can see every score at a glance."""
    cards = "".join(
        live_match_html(m, emap, games_by_match.get(m["id"], []), ev_by_id.get(m["event_id"]))
        for m in matches)
    st.markdown(f'<div class="pk-live-grid">{cards}</div>', unsafe_allow_html=True)


def render_result(m, emap, games, ev=None):
    a, b = m["entry_a_id"], m["entry_b_id"]
    wa = m["winner_entry_id"] == a
    an, bn = html.escape(_name(a, emap)), html.escape(_name(b, emap))
    if m["status"] == STATUS_BYE:
        meta = f'{html.escape(match_title(m, ev))} · {tr("walkover")}'
        winner = an if wa or b is None else bn
        st.markdown(
            f'<div class="pk-card done"><div class="meta">{meta}</div>'
            f'<div class="row"><span class="side win">{winner}</span>'
            f'<span class="pts">{tr("bye")}</span></div></div>', unsafe_allow_html=True)
        return
    meta = f'{html.escape(match_title(m, ev))} · {ago(m["finished_at"])}'
    st.markdown(
        f'<div class="pk-card done"><div class="meta">{meta}</div>'
        f'<div class="row"><span class="side {"win" if wa else "loss"}">{an}</span>'
        f'<span class="pts">{score_string(games, "a")}</span></div>'
        f'<div class="row"><span class="side {"win" if not wa else "loss"}">{bn}</span>'
        f'<span class="pts">{score_string(games, "b")}</span></div></div>',
        unsafe_allow_html=True)


def render_upcoming(m, emap, ev=None):
    a = html.escape(_name(m["entry_a_id"], emap))
    b = html.escape(_name(m["entry_b_id"], emap))
    court = f' · {html.escape(m["court"])}' if m["court"] else ""
    st.markdown(
        f'<div class="pk-card next"><div class="meta">{html.escape(match_title(m, ev))}{court}</div>'
        f'<div class="row"><span class="side">{a}</span></div>'
        f'<div class="row"><span class="side">{b}</span></div></div>',
        unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Bracket rendering
# --------------------------------------------------------------------------

def render_bracket(matches, emap, games_by_match, title=None):
    """Columns of matches, one column per round."""
    if not matches:
        empty_state(tr("No bracket yet."))
        return
    rounds: dict[int, list] = {}
    for m in matches:
        rounds.setdefault(m["round_no"], []).append(m)

    cols_html = []
    for rno in sorted(rounds):
        ms = sorted(rounds[rno], key=lambda m: m["match_no"])
        label = i18n.round_label(ms[0].get("round_label")) or tr("Round {n}", n=rno)
        nodes = [f'<div class="rlabel">{html.escape(label)}</div>']
        for m in ms:
            gs = games_by_match.get(m["id"], [])
            live = m["status"] == STATUS_LIVE
            rows = []
            for side, eid in (("a", m["entry_a_id"]), ("b", m["entry_b_id"])):
                nm = _name(eid, emap)
                cls = "tbd" if eid is None else ""
                if m["winner_entry_id"] and eid == m["winner_entry_id"]:
                    cls = "win"
                pts = score_string(gs, side) if gs else (tr("bye") if m["status"] == STATUS_BYE else "")
                rows.append(
                    f'<div class="n-row {cls}"><span>{html.escape(nm)}</span>'
                    f'<span class="n-pts">{html.escape(pts)}</span></div>')
            cap = ""
            if live:
                cap = (f'<div class="n-cap">● {tr("live")}'
                       + (f' · {html.escape(m["court"])}' if m["court"] else "") + '</div>')
            elif m["court"] and m["status"] == STATUS_PENDING:
                cap = f'<div class="n-cap">{html.escape(m["court"])}</div>'
            nodes.append(f'<div class="pk-node {"live" if live else ""}">{"".join(rows)}{cap}</div>')
        cols_html.append(f'<div class="pk-round">{"".join(nodes)}</div>')

    if title:
        st.markdown(f"**{title}**")
    st.markdown(f'<div class="pk-bracket">{"".join(cols_html)}</div>', unsafe_allow_html=True)


def standings_frame(rows, swiss=False):
    """Standings rows shaped for st.dataframe."""
    out = []
    for r in rows:
        item = {
            "#": r["rank"],
            tr("Entry"): r["name"] + (tr("  (withdrawn)") if r.get("status") == "withdrawn" else ""),
            tr("P"): r["played"], tr("W"): r["wins"], tr("L"): r["losses"],
            tr("Win %"): round(r["win_pct"] * 100, 1),
            tr("Games"): f"{r['games_won']}–{r['games_lost']}",
            tr("Pts"): f"{r['points_for']}–{r['points_against']}",
            tr("Diff"): r["point_diff"],
        }
        if r.get("pool"):
            item[tr("Pool")] = r["pool"]
        if swiss:
            item["Buchholz"] = r["buchholz"]
        out.append(item)
    return out
