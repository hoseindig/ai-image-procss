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
    face_quality_enabled: bool = Field(default=True)
    face_quality_min_face_width: float = Field(default=80.0, gt=0.0)
    face_quality_min_face_height: float = Field(default=80.0, gt=0.0)
    # Laplacian variance on the face crop. Tunable heuristic, not a blur probability.
    face_quality_min_sharpness: float = Field(default=60.0, ge=0.0)
    # Mean grayscale brightness in [0, 255]. Tunable heuristics.
    face_quality_min_brightness: float = Field(default=40.0, ge=0.0, le=255.0)
    face_quality_max_brightness: float = Field(default=220.0, ge=0.0, le=255.0)
    face_alignment_enabled: bool = Field(default=True)
    # Default 112×112 matches the planned SFace input; kept configurable.
    face_alignment_width: int = Field(default=112, ge=16)
    face_alignment_height: int = Field(default=112, ge=16)
    face_embedding_enabled: bool = Field(default=True)
    face_embedding_model_path: str = Field(default="models/face/sface/2021dec.onnx")
    face_embedding_threads: int = Field(default=2, ge=1)
    face_recognition_enabled: bool = Field(default=True)
    # OpenCV SFace FR_COSINE / LFW engineering default; match when similarity >= threshold.
    face_recognition_threshold: float = Field(default=0.363, ge=0.0, le=1.0)
    event_logging_enabled: bool = Field(default=True)
    event_recognized_cooldown_seconds: float = Field(default=10.0, ge=0.0)
    event_unknown_cooldown_seconds: float = Field(default=10.0, ge=0.0)
    # Purge events older than this many days on application startup (people/enrollments kept).
    event_retention_days: int = Field(default=90, ge=1)
    event_retention_enabled: bool = Field(default=True)
    event_api_default_page_size: int = Field(default=50, ge=1, le=500)
    event_api_max_page_size: int = Field(default=200, ge=1, le=1000)
    # TEST ONLY. Default false. Never enable automatically for production webcam use.
    # Gates POST /api/test/recognize and RecognitionTestService.
    recognition_test_mode: bool = Field(default=False)
    # When true, POST /cameras/{id}/start recovers from ERROR/CLOSED by close→open→start.
    # Not a background reconnect loop.
    camera_recover_on_start: bool = Field(default=True)
    # Consecutive failed VideoCapture.read() calls before ERROR (capture thread).
    camera_max_consecutive_read_failures: int = Field(default=30, ge=1, le=1000)

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        allowed = {"development", "test", "production"}
        if value not in allowed:
            raise ValueError(f"APP_ENV must be one of: {', '.join(sorted(allowed))}")
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

    @model_validator(mode="after")
    def validate_brightness_range(self) -> Self:
        if self.face_quality_min_brightness > self.face_quality_max_brightness:
            raise ValueError("FACE_QUALITY_MIN_BRIGHTNESS must be <= FACE_QUALITY_MAX_BRIGHTNESS")
        return self

    @model_validator(mode="after")
    def validate_event_page_sizes(self) -> Self:
        if self.event_api_default_page_size > self.event_api_max_page_size:
            raise ValueError("EVENT_API_DEFAULT_PAGE_SIZE must be <= EVENT_API_MAX_PAGE_SIZE")
        return self

    @model_validator(mode="after")
    def validate_production_hardening(self) -> Self:
        if self.app_env != "production":
            return self
        if self.debug:
            raise ValueError("DEBUG must be false when APP_ENV=production")
        if self.recognition_test_mode:
            raise ValueError("RECOGNITION_TEST_MODE must be false when APP_ENV=production")
        return self

    @model_validator(mode="after")
    def validate_enabled_model_paths(self) -> Self:
        """Fail fast when required ONNX files are missing (not in APP_ENV=test)."""
        if self.app_env == "test":
            return self
        checks: list[tuple[bool, str, str]] = [
            (
                self.face_detection_enabled,
                self.face_detection_model_path,
                "FACE_DETECTION_MODEL_PATH",
            ),
            (
                self.face_embedding_enabled,
                self.face_embedding_model_path,
                "FACE_EMBEDDING_MODEL_PATH",
            ),
        ]
        for enabled, relative, label in checks:
            if not enabled:
                continue
            path = Path(relative)
            if not path.is_absolute():
                path = (PROJECT_ROOT / path).resolve()
            if not path.is_file():
                raise ValueError(
                    f"{label} does not point to an existing file: {path}. "
                    "Install models with: python scripts/download_models.py"
                )
        return self


def load_settings() -> Settings:
    """Load settings from the environment and `.env` files."""
    return Settings()
