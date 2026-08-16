from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import resolve_database_url
from tests.helpers import IsolatedSettings


def test_default_cors_is_not_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "APP_NAME",
        "APP_ENV",
        "DEBUG",
        "HOST",
        "PORT",
        "DATABASE_URL",
        "LOG_LEVEL",
        "CORS_ORIGINS",
    ):
        monkeypatch.delenv(key, raising=False)
    settings = IsolatedSettings()
    assert "*" not in settings.cors_origins
    assert "http://localhost:3000" in settings.cors_origins


def test_cors_origins_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, http://127.0.0.1:3000")
    settings = IsolatedSettings()
    assert settings.cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IsolatedSettings(cors_origins=["*"])


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IsolatedSettings(log_level="VERBOSE")


def test_relative_sqlite_url_is_resolved_to_absolute() -> None:
    resolved = resolve_database_url("sqlite:///./data/app.db")
    assert resolved.startswith("sqlite:///")
    assert "data" in resolved
    assert "./data/app.db" not in resolved
    assert ":memory:" not in resolved


def test_memory_sqlite_url_is_unchanged() -> None:
    assert resolve_database_url("sqlite:///:memory:") == "sqlite:///:memory:"
