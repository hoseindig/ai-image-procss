"""Alembic upgrade / downgrade for person enrollment schema."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import BACKEND_ROOT, resolve_database_url


@pytest.fixture
def alembic_database_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    db_path = tmp_path / "alembic_person.db"
    url = resolve_database_url(f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("DATABASE_URL", url)
    # Prevent project .env from overriding if somehow preferred incorrectly.
    monkeypatch.chdir(BACKEND_ROOT)
    return url


def _alembic_config() -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


def test_alembic_upgrade_downgrade_upgrade(alembic_database_url: str) -> None:
    cfg = _alembic_config()
    command.upgrade(cfg, "head")

    engine = create_engine(alembic_database_url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert "persons" in tables
        assert "enrollment_samples" in tables
        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert version == "0002_person_enrollment"
    finally:
        engine.dispose()

    command.downgrade(cfg, "0001_initial")
    engine = create_engine(alembic_database_url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert "persons" not in tables
        assert "enrollment_samples" not in tables
        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert version == "0001_initial"
    finally:
        engine.dispose()

    command.upgrade(cfg, "head")
    engine = create_engine(alembic_database_url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert "persons" in tables
        assert "enrollment_samples" in tables
    finally:
        engine.dispose()
