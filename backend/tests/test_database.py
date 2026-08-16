from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, literal, select

from app.db.base import Base
from app.db.session import Database, ensure_sqlite_directory


def test_sqlite_directory_is_created(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "dir" / "app.db"
    url = f"sqlite:///{db_path.as_posix()}"
    ensure_sqlite_directory(url)
    assert db_path.parent.is_dir()


def test_database_session_can_execute(tmp_path: Path) -> None:
    db_path = tmp_path / "session.db"
    database = Database(f"sqlite:///{db_path.as_posix()}")
    try:
        with database.session() as session:
            value = session.scalar(select(literal(1)))
            assert value == 1
        assert db_path.exists()
        inspector = inspect(database.engine)
        assert inspector.get_table_names() == []
    finally:
        database.dispose()


def test_metadata_create_all_on_empty_schema(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")
    try:
        Base.metadata.create_all(database.engine)
        with database.session() as session:
            assert session.scalar(select(literal(1))) == 1
    finally:
        database.dispose()
