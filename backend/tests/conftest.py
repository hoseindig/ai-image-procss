"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.helpers import IsolatedSettings


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    for key in (
        "APP_NAME",
        "APP_ENV",
        "DEBUG",
        "HOST",
        "PORT",
        "DATABASE_URL",
        "LOG_LEVEL",
        "CORS_ORIGINS",
        "CAMERA_DEFAULT_ID",
        "CAMERA_DEFAULT_NAME",
        "CAMERA_DEVICE_INDEX",
        "CAMERA_WIDTH",
        "CAMERA_HEIGHT",
        "CAMERA_FPS",
        "CAMERA_BACKEND",
        "FACE_DETECTION_ENABLED",
        "FACE_DETECTION_MODEL_PATH",
        "FACE_DETECTION_CONFIDENCE_THRESHOLD",
        "FACE_DETECTION_NMS_THRESHOLD",
        "FACE_DETECTION_INPUT_WIDTH",
        "FACE_DETECTION_INPUT_HEIGHT",
        "FACE_DETECTION_MAX_FACES",
        "FACE_DETECTION_INFERENCE_INTERVAL_MS",
        "FACE_TRACKING_ENABLED",
        "FACE_TRACKING_IOU_THRESHOLD",
        "FACE_TRACKING_MAX_CENTROID_DISTANCE",
        "FACE_TRACKING_MAX_MISSED_FRAMES",
        "FACE_TRACKING_MIN_CONFIRMED_FRAMES",
        "FACE_TRACKING_MAX_TRACKS",
        "FACE_QUALITY_ENABLED",
        "FACE_QUALITY_MIN_FACE_WIDTH",
        "FACE_QUALITY_MIN_FACE_HEIGHT",
        "FACE_QUALITY_MIN_SHARPNESS",
        "FACE_QUALITY_MIN_BRIGHTNESS",
        "FACE_QUALITY_MAX_BRIGHTNESS",
        "FACE_ALIGNMENT_ENABLED",
        "FACE_ALIGNMENT_WIDTH",
        "FACE_ALIGNMENT_HEIGHT",
        "FACE_EMBEDDING_ENABLED",
        "FACE_EMBEDDING_MODEL_PATH",
        "FACE_EMBEDDING_THREADS",
        "FACE_RECOGNITION_ENABLED",
        "FACE_RECOGNITION_THRESHOLD",
    ):
        monkeypatch.delenv(key, raising=False)
    database_path = tmp_path / "test.db"
    return IsolatedSettings(
        app_name="Local Face Camera",
        app_env="test",
        debug=True,
        host="127.0.0.1",
        port=8000,
        database_url=f"sqlite:///{database_path.as_posix()}",
        log_level="INFO",
        cors_origins=["http://localhost:3000"],
        face_detection_enabled=False,
        face_embedding_enabled=False,
        face_recognition_enabled=False,
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    application = create_app(settings)
    with TestClient(application) as test_client:
        yield test_client
