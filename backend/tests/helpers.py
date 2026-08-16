"""Test helpers. Not part of the application runtime."""

from __future__ import annotations

from pydantic_settings import SettingsConfigDict

from app.core.config import Settings


class IsolatedSettings(Settings):
    """Settings subclass that ignores `.env` files.

    `_env_file` is a pydantic-settings constructor hook, not a model field, so
    tests use this subclass instead of a `# type: ignore`.
    """

    model_config = SettingsConfigDict(
        env_file=None,
        extra="ignore",
        case_sensitive=False,
    )
