"""Versioned schema upgrades; use the same settings and cwd as API/worker."""

from contextlib import nullcontext
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from filelock import FileLock

HEAD = "0002_privacy"


def upgrade(engine):
    database = engine.url.database
    lock = FileLock(str(Path(database).resolve()) + ".migration.lock", timeout=60) if engine.dialect.name == "sqlite" and database not in (None, ":memory:") else nullcontext()
    with lock:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")


def require_current(engine):
    with engine.connect() as connection:
        if MigrationContext.configure(connection).get_current_revision() != HEAD:
            raise RuntimeError("Database needs migration. Run python -m app.db.migrate before starting the worker")


def main():
    from app.core.config import Settings
    from app.db.session import create_database

    engine, _ = create_database(Settings())
    engine.dispose()
    print(f"Database migration complete: {HEAD}")


if __name__ == "__main__":
    main()
