from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.models.entities import Base


def create_database(settings):
    url = make_url(settings.database_url)
    if url.drivername.startswith("sqlite") and url.database and url.database != ":memory:":
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    options = {"check_same_thread": False, "timeout": 30} if url.drivername.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, connect_args=options, pool_pre_ping=True)
    if url.drivername.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def sqlite_pragmas(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)
