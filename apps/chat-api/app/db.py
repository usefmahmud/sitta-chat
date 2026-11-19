"""SQLAlchemy engine, session factory and schema bootstrap.

SQLite is opened with WAL so a reader never blocks a writer, which matters for
a chat backend where message inserts and list queries run concurrently.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """Declarative base shared by every model."""


def _ensure_sqlite_directory(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    path = url[len("sqlite:///") :]
    if path in ("", ":memory:"):
        return
    pathlib.Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)


def build_engine(url: str | None = None) -> Engine:
    database_url = url or get_settings().database_url
    _ensure_sqlite_directory(database_url)

    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    engine = create_engine(database_url, connect_args=connect_args, future=True)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            # Writers wait for the lock instead of failing with
            # "database is locked" under concurrent sends (risk R1).
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


engine = build_engine()
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False, class_=Session
)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create missing tables. Real migrations arrive with a later ticket."""
    from . import models  # noqa: F401  (import registers the mappers)

    Base.metadata.create_all(bind=engine)
