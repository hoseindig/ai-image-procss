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


def test_face_detection_defaults() -> None:
    settings = IsolatedSettings()
    assert settings.face_detection_enabled is True
    assert settings.face_detection_model_path == "models/face/yunet/2023mar.onnx"
    assert settings.face_detection_confidence_threshold == 0.7
    assert settings.face_detection_input_width == 640
    assert settings.face_detection_input_height == 640
    assert settings.face_detection_inference_interval_ms == 100
    assert settings.face_tracking_enabled is True
    assert settings.face_tracking_iou_threshold == 0.3
    assert settings.face_tracking_max_centroid_distance == 100.0
    assert settings.face_tracking_max_missed_frames == 5
    assert settings.face_tracking_min_confirmed_frames == 2
    assert settings.face_tracking_max_tracks == 20
    assert settings.face_quality_enabled is True
    assert settings.face_quality_min_face_width == 80.0
    assert settings.face_quality_min_face_height == 80.0
    assert settings.face_quality_min_sharpness == 60.0
    assert settings.face_quality_min_brightness == 40.0
    assert settings.face_quality_max_brightness == 220.0
    assert settings.face_alignment_enabled is True
    assert settings.face_alignment_width == 112
    assert settings.face_alignment_height == 112
    assert settings.face_embedding_enabled is True
    assert settings.face_embedding_model_path == "models/face/sface/2021dec.onnx"
    assert settings.face_embedding_threads == 2
    assert settings.face_recognition_enabled is True
    assert settings.face_recognition_threshold == 0.363
    assert settings.event_logging_enabled is True
    assert settings.event_recognized_cooldown_seconds == 10.0
    assert settings.event_unknown_cooldown_seconds == 10.0
    assert settings.event_retention_days == 90


def test_invalid_confidence_threshold_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IsolatedSettings(face_detection_confidence_threshold=1.5)


def test_invalid_tracking_iou_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IsolatedSettings(face_tracking_iou_threshold=1.5)


def test_invalid_brightness_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IsolatedSettings(
            face_quality_min_brightness=200.0,
            face_quality_max_brightness=100.0,
        )
