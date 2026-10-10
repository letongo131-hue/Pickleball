"""Start the app on your own machine against a throwaway local database.

    python run_local.py                 # demo data in local/demo.db (created on first run)
    python run_local.py --reset         # wipe local/demo.db and re-seed it
    python run_local.py --empty         # start with an empty local/scratch.db instead
    python run_local.py --copy-of FILE  # work on a COPY of FILE (e.g. a backup of the
                                        # real pickleball.db) — the original is never opened
    python run_local.py --venue         # backup for match day: a real, kept database in
                                        # local/venue.db that tablets on the same Wi-Fi can open
    python run_local.py --port 8502     # any extra args go straight to `streamlit run`

Whatever you choose, the app is forced onto local SQLite: a Postgres URL in
.streamlit/secrets.toml or DATABASE_URL is ignored, so clicking around here
can't change the live tournament. The sidebar footer shows which file is in use.
Sign in with admin passcode `pickle` / referee `referee` unless your
secrets.toml sets others.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / "local"


def _wipe(path: Path):
    for suffix in ("", "-wal", "-shm", "-journal"):
        p = Path(str(path) + suffix)
        if p.exists():
            p.unlink()


def _lan_ip() -> str | None:
    """This laptop's address on the local network (no traffic is sent)."""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--empty", action="store_true", help="start with an empty database")
    group.add_argument("--copy-of", metavar="FILE", help="run on a copy of this SQLite file")
    group.add_argument("--venue", action="store_true",
                       help="match-day backup: keep data in local/venue.db and show the "
                            "address tablets on the same Wi-Fi should open")
    ap.add_argument("--reset", action="store_true", help="delete and recreate the local database")
    ap.add_argument("--port", default="8501", help="port to serve on (default 8501)")
    args, streamlit_args = ap.parse_known_args()
    streamlit_args = ["--server.port", str(args.port), *streamlit_args]

    LOCAL.mkdir(exist_ok=True)
    if args.copy_of:
        src = Path(args.copy_of).resolve()
        if not src.exists():
            print(f"No such file: {src}")
            return 1
        target = LOCAL / f"copy-of-{src.name}"
        if args.reset or not target.exists():
            _wipe(target)
            shutil.copy2(src, target)
            for suffix in ("-wal", "-shm"):
                side = Path(str(src) + suffix)
                if side.exists():
                    shutil.copy2(side, Path(str(target) + suffix))
            print(f"Copied {src.name} -> {target}")
        seed = False
    elif args.venue:
        target = LOCAL / "venue.db"
        if args.reset:
            print("--reset is ignored with --venue (it would delete the tournament).")
        seed = False
        port = args.port
        ip = _lan_ip()
        print("\nVENUE MODE — tablets and screens on the same Wi-Fi open:")
        print(f"    http://{ip}:{port}" if ip else
              "    http://<this laptop's IP address>:" + port)
        print("If they can't connect, allow Python through this laptop's firewall.\n")
    elif args.empty:
        target = LOCAL / "scratch.db"
        if args.reset:
            _wipe(target)
        seed = False
    else:
        target = LOCAL / "demo.db"
        if args.reset:
            _wipe(target)
        seed = not target.exists()

    os.environ["PICKLEBALL_DB"] = str(target)
    os.environ.setdefault("STREAMLIT_THEME_BASE", "light")
    os.environ.setdefault("STREAMLIT_CLIENT_TOOLBAR_MODE", "minimal")
    os.environ["PICKLEBALL_LOCAL"] = "1"
    os.environ.pop("DATABASE_URL", None)

    if seed:
        sys.path.insert(0, str(ROOT))
        from scripts.seed_demo import seed as seed_demo
        from tourney import db
        db.use_sqlite(str(target))
        seed_demo()
        db.reset_connection()
        print(f"Seeded a demo tournament into {target}")

    print(f"Database: {target}")
    print("Starting Streamlit — press Ctrl+C to stop.\n")
    cmd = [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"), *streamlit_args]
    try:
        return subprocess.call(cmd, cwd=str(ROOT))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
