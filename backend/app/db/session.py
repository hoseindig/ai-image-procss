"""Database engine and session factory.

Sessions are created per request (or per explicit context) and closed afterwards.
There is no process-wide shared Session object.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.logging import get_logger

logger = get_logger("app.db")


def ensure_sqlite_directory(url: str) -> None:
    """Create the parent directory for a file-backed SQLite database."""
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite":
        return
    database = parsed.database
    if database is None or database == ":memory:":
        return
    Path(database).parent.mkdir(parents=True, exist_ok=True)


def create_db_engine(url: str) -> Engine:
    """Create an engine from a SQLAlchemy URL.

    SQLite uses `check_same_thread=False` so FastAPI can check out connections
    from worker threads. Other backends (e.g. PostgreSQL later) ignore that flag.
    """
    ensure_sqlite_directory(url)
    parsed = make_url(url)
    is_sqlite = parsed.get_backend_name() == "sqlite"
    is_memory = is_sqlite and (parsed.database is None or parsed.database == ":memory:")

    connect_args: dict[str, bool] = {}
    if is_sqlite:
        connect_args["check_same_thread"] = False

    if is_memory:
        return create_engine(
            url,
            connect_args=connect_args,
            poolclass=StaticPool,
        )
    return create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


class Database:
    """Owns the engine and session factory for one application instance."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.engine = create_db_engine(url)
        self._session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )
        logger.info("Database engine created")

    @contextmanager
    def session(self) -> Iterator[Session]:
        db_session = self._session_factory()
        try:
            yield db_session
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    def dispose(self) -> None:
        self.engine.dispose()
        logger.info("Database engine disposed")
