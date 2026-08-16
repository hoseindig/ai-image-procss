"""Application configuration loaded from environment variables and `.env` files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine.url import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent

_ENV_FILES = (
    BACKEND_ROOT / ".env",
    PROJECT_ROOT / ".env",
)


def _parse_cors_origins(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            if not isinstance(parsed, list):
                raise ValueError("CORS_ORIGINS JSON value must be a list of strings")
            return [str(item).strip() for item in parsed if str(item).strip()]
        return [item.strip() for item in stripped.split(",") if item.strip()]
    raise TypeError("CORS_ORIGINS must be a string or list of strings")


def resolve_database_url(url: str) -> str:
    """Resolve relative SQLite paths against the project root.

    PostgreSQL (and other) URLs are returned unchanged so the same settings
    object can later point at a different engine without code changes.
    """
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite":
        return url
    database = parsed.database
    if database is None or database == ":memory:":
        return url
    path = Path(database)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return str(parsed.set(database=str(path)))


class Settings(BaseSettings):
    """Central application settings. Environment variables take precedence."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = Field(default="Local Face Camera")
    app_env: str = Field(default="development")
    debug: bool = Field(default=True)
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000, ge=1, le=65535)
    database_url: str = Field(default="sqlite:///./data/app.db")
    log_level: str = Field(default="INFO")
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    camera_default_id: str = Field(default="default")
    camera_default_name: str = Field(default="USB Webcam")
    camera_device_index: int = Field(default=0, ge=0)
    camera_width: int = Field(default=1280, ge=1)
    camera_height: int = Field(default=720, ge=1)
    camera_fps: float = Field(default=15.0, gt=0)
    camera_backend: str = Field(default="dshow")
    face_detection_enabled: bool = Field(default=True)
    face_detection_model_path: str = Field(default="models/face/yunet/2023mar.onnx")
    face_detection_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    face_detection_nms_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    face_detection_input_width: int = Field(default=640, ge=32)
    face_detection_input_height: int = Field(default=640, ge=32)
    face_detection_max_faces: int = Field(default=10, ge=1)
    face_detection_inference_interval_ms: int = Field(default=100, ge=1)
    face_tracking_enabled: bool = Field(default=True)
    face_tracking_iou_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    face_tracking_max_centroid_distance: float = Field(default=100.0, ge=0.0)
    face_tracking_max_missed_frames: int = Field(default=5, ge=0)
    face_tracking_min_confirmed_frames: int = Field(default=2, ge=1)
    face_tracking_max_tracks: int = Field(default=20, ge=1)

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if value not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        return _parse_cors_origins(value)

    @field_validator("database_url")
    @classmethod
    def resolve_sqlite_url(cls, value: str) -> str:
        return resolve_database_url(value)

    @field_validator("camera_backend", mode="before")
    @classmethod
    def normalize_camera_backend(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("camera_backend")
    @classmethod
    def validate_camera_backend(cls, value: str) -> str:
        allowed = {"dshow", "msmf", "any"}
        if value not in allowed:
            raise ValueError(f"CAMERA_BACKEND must be one of: {', '.join(sorted(allowed))}")
        return value

    @model_validator(mode="after")
    def reject_wildcard_cors(self) -> Self:
        if any(origin.strip() == "*" for origin in self.cors_origins):
            raise ValueError("CORS_ORIGINS cannot include '*' (wildcard origins are not allowed)")
        return self


def load_settings() -> Settings:
    """Load settings from the environment and `.env` files."""
    return Settings()
