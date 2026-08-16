from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.cameras.manager import CameraManager
from app.cameras.types import CameraConfig
from app.core.config import Settings
from app.main import create_app
from app.schemas.detection import DetectionResponse
from app.vision.exceptions import ModelNotFoundError
from tests.fake_camera import FakeCameraSource
from tests.fake_vision import FakeFaceDetector
from tests.yunet_helpers import sample_face


@pytest.fixture
def detection_client(settings: Settings) -> Iterator[TestClient]:
    def factory(config: CameraConfig) -> FakeCameraSource:
        return FakeCameraSource(config)

    manager = CameraManager(source_factory=factory)
    manager.register(
        CameraConfig(camera_id="default", name="Fake USB", width=64, height=48, fps=10)
    )
    enabled = settings.model_copy(update={"face_detection_enabled": True})
    detector = FakeFaceDetector([sample_face(x=8, y=6, width=20, height=22, confidence=0.91)])
    application = create_app(enabled, camera_manager=manager, face_detector=detector)
    with TestClient(application) as client:
        yield client


def test_detections_before_start_are_empty(detection_client: TestClient) -> None:
    response = detection_client.get("/api/cameras/default/detections")
    assert response.status_code == 200
    body = response.json()
    assert body["camera_id"] == "default"
    assert body["enabled"] is True
    assert body["faces"] == []
    assert body["timestamp"] is None


def test_start_camera_returns_latest_detections(detection_client: TestClient) -> None:
    started = detection_client.post("/api/cameras/default/start")
    assert started.status_code == 200
    body = _wait_for_detection(detection_client)
    assert len(body.faces) == 1
    face = body.faces[0]
    assert face.confidence == 0.91
    assert face.bounding_box.x == 8.0
    assert face.bounding_box.y == 6.0
    assert face.bounding_box.width == 20.0
    assert face.bounding_box.height == 22.0
    assert face.landmarks.left_eye is not None
    assert face.landmarks.right_eye is not None
    assert face.landmarks.nose is not None
    assert face.landmarks.left_mouth is not None
    assert face.landmarks.right_mouth is not None
    status = detection_client.get("/api/system/status").json()
    assert status["face_detection"]["enabled"] is True
    assert status["face_detection"]["model_loaded"] is True
    assert status["face_detection"]["provider"] == "test"
    detection_client.post("/api/cameras/default/stop")


def test_unknown_camera_detections_are_404(detection_client: TestClient) -> None:
    response = detection_client.get("/api/cameras/missing/detections")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "camera_not_found"


def test_missing_model_fails_at_startup(settings: Settings, tmp_path: Path) -> None:
    enabled = settings.model_copy(
        update={
            "face_detection_enabled": True,
            "face_detection_model_path": str(tmp_path / "no-such-model.onnx"),
        }
    )
    application = create_app(enabled)
    with (
        pytest.raises(ModelNotFoundError, match="YuNet model not found"),
        TestClient(application),
    ):
        pass


def _wait_for_detection(client: TestClient) -> DetectionResponse:
    deadline = time.monotonic() + 2.0
    latest = DetectionResponse(camera_id="default", enabled=True)
    while time.monotonic() < deadline:
        response = client.get("/api/cameras/default/detections")
        assert response.status_code == 200
        latest = DetectionResponse.model_validate(response.json())
        if latest.faces:
            return latest
        time.sleep(0.01)
    return latest
