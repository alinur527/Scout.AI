"""Create a consistent SQLite backup without overwriting an existing file."""

import argparse
import os
from pathlib import Path
import sqlite3
import sys

from pydantic import ValidationError
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import Settings  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    destination = parser.parse_args().destination.resolve()
    os.chdir(ROOT / "backend")
    try:
        url = make_url(Settings().database_url)
    except ValidationError:
        raise SystemExit("Invalid configuration; run doctor. Configuration values are hidden.") from None
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        raise SystemExit("This backup command supports file-based SQLite only")
    source = Path(url.database).resolve()
    if not source.is_file():
        raise SystemExit("Configured SQLite database does not exist")
    # Exclusive creation refuses an existing backup (including the source DB).
    with destination.open("xb"):
        pass
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as original, sqlite3.connect(destination) as backup:
        original.backup(backup)
        if backup.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise SystemExit("Backup integrity check failed; do not restore this file")
    print(f"Verified SQLite backup: {destination}. Treat it as private user data.")


if __name__ == "__main__":
    main()
