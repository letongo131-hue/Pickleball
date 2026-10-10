"""Storage layer.

Defaults to a local SQLite file (great for a laptop scoring table on the same
Wi-Fi). If you put a Postgres URL in Streamlit secrets it uses that instead,
which is what you want on Streamlit Community Cloud because the container disk
is wiped whenever the app sleeps or redeploys.

    # .streamlit/secrets.toml
    [database]
    url = "postgresql://user:pass@host:5432/dbname?sslmode=require"

Which database gets used, in priority order:

1. ``PICKLEBALL_DB=/some/file.db``  -> that SQLite file, always. Any Postgres
   URL in secrets or ``DATABASE_URL`` is ignored. This is what the tests and
   ``run_local.py`` use, so a local test run can never touch the live
   tournament database by accident.
2. ``PICKLEBALL_LOCAL=1``           -> the default SQLite file, same guarantee.
3. ``DATABASE_URL`` env var         -> Postgres.
4. ``[database].url`` in secrets    -> Postgres (Streamlit Cloud).
5. otherwise                        -> ``pickleball.db`` next to ``app.py``.

Streamlit itself is only imported to read secrets in cases 4/5, so the
engine runs (and is testable) without Streamlit installed.
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.RLock()
_STATE: dict = {"backend": None, "conn": None, "ready": False, "where": None, "used": 0.0}

# A hosted Postgres (Neon's free plan, for one) suspends after a few idle
# minutes and silently drops open connections. Before reusing a connection that
# has been idle longer than this, check it with a cheap ping and reconnect if it
# is gone — otherwise the first tap after a quiet spell would fail.
IDLE_PING_SECONDS = 60

# The project folder (the one holding app.py). The default SQLite file lives
# here regardless of which directory you launch from — running a test from
# tests/ or hitting F5 in VSCode from a parent folder used to silently create
# a second, empty pickleball.db wherever the current directory happened to be.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_FILE = PROJECT_ROOT / "pickleball.db"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def _forced_local() -> bool:
    return bool(os.environ.get("PICKLEBALL_DB")) or _truthy(os.environ.get("PICKLEBALL_LOCAL"))


def sqlite_path() -> str:
    """The SQLite file in use (or that would be used)."""
    return os.environ.get("PICKLEBALL_DB") or str(DEFAULT_SQLITE_FILE)


def _database_url() -> str | None:
    if _forced_local():
        return None
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        import streamlit as st

        return st.secrets["database"]["url"]
    except Exception:
        return None


def _connect():
    url = _database_url()
    if url and url.startswith(("postgres://", "postgresql://")):
        import psycopg2  # noqa: F401  (only needed for the Postgres path)
        import psycopg2.extras

        conn = psycopg2.connect(
            url, connect_timeout=10,
            # A free-tier host can silently drop an idle connection; without
            # keepalives the driver just hangs until the OS notices, which
            # looks exactly like "everything is slow" rather than an error.
            keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5,
        )
        conn.autocommit = False
        host = re.sub(r"^.*@", "", url).split("/")[0].split("?")[0]
        return "postgres", conn, host

    path = sqlite_path()
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")       # concurrent readers while one admin writes
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.commit()
    return "sqlite", conn, os.path.abspath(path)


def _alive(conn) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchall()
        cur.close()
        conn.rollback()
        return True
    except Exception:
        return False


def _ensure():
    if _STATE["ready"]:
        return
    with _LOCK:
        if _STATE["ready"]:
            return
        old = _STATE["conn"]
        if old is not None:
            try:
                old.close()
            except Exception:
                pass
        backend_name, conn, where = _connect()
        _STATE["backend"] = backend_name
        _STATE["conn"] = conn
        _STATE["where"] = where
        _create_schema(conn, backend_name)
        _STATE["ready"] = True


def backend() -> str:
    _ensure()
    return _STATE["backend"]


def describe() -> str:
    """Human-readable 'which database am I on', for the sidebar footer."""
    _ensure()
    if _STATE["backend"] == "postgres":
        return f"postgres · {_STATE['where']}"
    return f"sqlite · {os.path.basename(_STATE['where'])}"


def _adapt(sql: str) -> str:
    if _STATE["backend"] == "postgres":
        sql = sql.replace("?", "%s")
    return sql


@contextmanager
def cursor(commit: bool = False):
    """One short-lived cursor under a process lock.

    Transactions are deliberately tiny: two admins typing scores at the same
    time only ever contend for microseconds.
    """
    _ensure()
    with _LOCK:
        if (_STATE["backend"] == "postgres"
                and time.monotonic() - _STATE["used"] > IDLE_PING_SECONDS
                and not _alive(_STATE["conn"])):
            _STATE["ready"] = False
            _ensure()
        _STATE["used"] = time.monotonic()
        conn = _STATE["conn"]
        cur = conn.cursor()
        try:
            yield cur
            if commit:
                conn.commit()
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                # The connection itself is dead (a host-side idle timeout,
                # a network blip) — rollback can't work on a broken
                # connection. Mark it for a fresh reconnect on the *next*
                # call instead of leaving the app wedged until it's
                # restarted; this operation still fails, but the next one
                # won't.
                _STATE["ready"] = False
            raise exc
        finally:
            cur.close()


def _rows_to_dicts(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


def query(sql: str, params: tuple = ()) -> list[dict]:
    with cursor() as cur:
        cur.execute(_adapt(sql), params)
        return _rows_to_dicts(cur, cur.fetchall())


def query_one(sql: str, params: tuple = ()) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()) -> int:
    with cursor(commit=True) as cur:
        cur.execute(_adapt(sql), params)
        return cur.rowcount


def insert(table: str, data: dict) -> int:
    _ensure()
    cols = list(data.keys())
    placeholders = ", ".join(["?"] * len(cols))
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    if _STATE["backend"] == "postgres":
        sql += " RETURNING id"
    with cursor(commit=True) as cur:
        cur.execute(_adapt(sql), tuple(data.values()))
        if _STATE["backend"] == "postgres":
            return cur.fetchone()[0]
        return cur.lastrowid


def update(table: str, row_id: int, data: dict) -> int:
    if not data:
        return 0
    sets = ", ".join(f"{c} = ?" for c in data)
    sql = f"UPDATE {table} SET {sets} WHERE id = ?"
    return execute(sql, tuple(data.values()) + (row_id,))


SCHEMA = """
CREATE TABLE IF NOT EXISTS tournaments (
    id {PK},
    name TEXT NOT NULL,
    venue TEXT,
    start_date TEXT,
    end_date TEXT,
    status TEXT NOT NULL DEFAULT 'setup',
    notes TEXT,
    is_quick INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id {PK},
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    format TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'setup',
    best_of INTEGER NOT NULL DEFAULT 3,
    scoring TEXT NOT NULL DEFAULT '11_rally_2',
    swiss_rounds INTEGER DEFAULT 5,
    pool_count INTEGER DEFAULT 2,
    advance_per_pool INTEGER DEFAULT 2,
    gf_reset INTEGER NOT NULL DEFAULT 1,
    draw_method TEXT,
    scoring_system TEXT NOT NULL DEFAULT 'side_out',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    id {PK},
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    gender TEXT,
    club TEXT,
    rating REAL,
    contact TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT
);

CREATE TABLE IF NOT EXISTS entries (
    id {PK},
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    player1_id INTEGER REFERENCES players(id) ON DELETE SET NULL,
    player2_id INTEGER REFERENCES players(id) ON DELETE SET NULL,
    seed INTEGER,
    pool TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    created_by TEXT
);

CREATE TABLE IF NOT EXISTS matches (
    id {PK},
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    stage TEXT NOT NULL DEFAULT 'main',
    pool TEXT,
    round_no INTEGER NOT NULL DEFAULT 1,
    round_label TEXT,
    match_no INTEGER NOT NULL DEFAULT 1,
    court TEXT,
    entry_a_id INTEGER REFERENCES entries(id) ON DELETE SET NULL,
    entry_b_id INTEGER REFERENCES entries(id) ON DELETE SET NULL,
    a_void INTEGER NOT NULL DEFAULT 0,
    b_void INTEGER NOT NULL DEFAULT 0,
    best_of INTEGER NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'pending',
    winner_entry_id INTEGER REFERENCES entries(id) ON DELETE SET NULL,
    loser_entry_id INTEGER REFERENCES entries(id) ON DELETE SET NULL,
    next_match_id INTEGER,
    next_slot TEXT,
    loser_next_match_id INTEGER,
    loser_next_slot TEXT,
    started_at TEXT,
    finished_at TEXT,
    cur_a INTEGER NOT NULL DEFAULT 0,
    cur_b INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT,
    updated_by TEXT,
    locked_by TEXT,
    locked_at TEXT,
    serve_state TEXT
);

CREATE TABLE IF NOT EXISTS games (
    id {PK},
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    game_no INTEGER NOT NULL,
    score_a INTEGER NOT NULL DEFAULT 0,
    score_b INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rallies (
    id {PK},
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    game_no INTEGER NOT NULL,
    seq INTEGER NOT NULL,
    kind TEXT NOT NULL,
    winner TEXT,
    a_before INTEGER NOT NULL DEFAULT 0,
    b_before INTEGER NOT NULL DEFAULT 0,
    a_after INTEGER NOT NULL DEFAULT 0,
    b_after INTEGER NOT NULL DEFAULT 0,
    state_before TEXT,
    state_after TEXT,
    created_at TEXT NOT NULL,
    actor TEXT
);

CREATE TABLE IF NOT EXISTS courts (
    id {PK},
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id {PK},
    ts TEXT NOT NULL,
    actor TEXT,
    tournament_id INTEGER,
    entity TEXT,
    entity_id INTEGER,
    action TEXT,
    detail TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_tournament ON events(tournament_id);
CREATE INDEX IF NOT EXISTS idx_players_tournament ON players(tournament_id);
CREATE INDEX IF NOT EXISTS idx_entries_event ON entries(event_id);
CREATE INDEX IF NOT EXISTS idx_matches_event ON matches(event_id);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_games_match ON games(match_id);
CREATE INDEX IF NOT EXISTS idx_rallies_match ON rallies(match_id, game_no, seq);
CREATE INDEX IF NOT EXISTS idx_courts_tournament ON courts(tournament_id);
"""


def _create_schema(conn, backend_name: str):
    pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if backend_name == "sqlite" else "SERIAL PRIMARY KEY"
    ddl = SCHEMA.replace("{PK}", pk)
    cur = conn.cursor()
    for stmt in [s.strip() for s in ddl.split(";") if s.strip()]:
        cur.execute(stmt)
    conn.commit()
    _migrate(conn, cur, backend_name)
    cur.close()


# Columns added after the initial release. CREATE TABLE IF NOT EXISTS above
# only builds a table from scratch — an existing database file needs these
# added by hand, once, harmlessly skipped if already present.
_MIGRATIONS = [
    ("matches", "cur_a", "INTEGER NOT NULL DEFAULT 0"),
    ("matches", "cur_b", "INTEGER NOT NULL DEFAULT 0"),
    ("tournaments", "is_quick", "INTEGER NOT NULL DEFAULT 0"),
    ("events", "draw_method", "TEXT"),
    ("events", "scoring_system", "TEXT NOT NULL DEFAULT 'side_out'"),
    ("matches", "serve_state", "TEXT"),
]


def _migrate(conn, cur, backend_name: str):
    for table, column, coltype in _MIGRATIONS:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
            conn.commit()
        except Exception:
            conn.rollback()   # column already exists — nothing to do


def log(actor: str | None, tournament_id: int | None, entity: str,
        entity_id: int | None, action: str, detail: str = ""):
    insert("audit_log", {
        "ts": now(), "actor": actor or "system", "tournament_id": tournament_id,
        "entity": entity, "entity_id": entity_id, "action": action,
        "detail": detail[:2000],
    })


def reset_connection():
    """Drop the cached connection (used after switching database files)."""
    with _LOCK:
        try:
            if _STATE["conn"]:
                _STATE["conn"].close()
        except Exception:
            pass
        _STATE.update({"backend": None, "conn": None, "ready": False, "where": None, "used": 0.0})


def use_sqlite(path: str, fresh: bool = False):
    """Point this process at a specific SQLite file from now on.

    `fresh=True` deletes the file (and its WAL/SHM side files) first, which is
    what a test wants. Sets PICKLEBALL_DB too, so anything that reads the
    environment later — a Streamlit AppTest script, say — lands on the same
    file instead of the live database.
    """
    reset_connection()
    path = os.path.abspath(path)
    if fresh:
        for suffix in ("", "-wal", "-shm", "-journal"):
            try:
                os.remove(path + suffix)
            except FileNotFoundError:
                pass
    os.environ["PICKLEBALL_DB"] = path
    return path


_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def dump_all() -> dict:
    """Whole database as plain dicts, for the JSON backup button."""
    tables = ["tournaments", "events", "players", "entries", "matches", "games",
              "courts", "rallies", "audit_log"]
    out = {}
    for t in tables:
        assert _IDENT.match(t)
        out[t] = query(f"SELECT * FROM {t} ORDER BY id")
    return out
