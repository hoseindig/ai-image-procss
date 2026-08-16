from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.cameras.manager import CameraManager
from app.cameras.types import CameraConfig, CameraState
from app.core.config import Settings
from app.main import create_app
from tests.fake_camera import FakeCameraSource


@pytest.fixture
def camera_client(settings: Settings) -> Iterator[TestClient]:
    def factory(config: CameraConfig) -> FakeCameraSource:
        return FakeCameraSource(config)

    manager = CameraManager(source_factory=factory)
    manager.register(
        CameraConfig(camera_id="default", name="Fake USB", width=64, height=48, fps=10)
    )
    application = create_app(settings, camera_manager=manager)
    with TestClient(application) as client:
        yield client


def test_list_cameras(camera_client: TestClient) -> None:
    response = camera_client.get("/api/cameras")
    assert response.status_code == 200
    body = response.json()
    assert len(body["cameras"]) == 1
    assert body["cameras"][0]["id"] == "default"
    assert body["cameras"][0]["state"] == CameraState.CLOSED


def test_get_camera(camera_client: TestClient) -> None:
    response = camera_client.get("/api/cameras/default")
    assert response.status_code == 200
    assert response.json()["name"] == "Fake USB"


def test_get_unknown_camera(camera_client: TestClient) -> None:
    response = camera_client.get("/api/cameras/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "camera_not_found"
    assert "Traceback" not in response.text


def test_start_and_stop_camera(camera_client: TestClient) -> None:
    started = camera_client.post("/api/cameras/default/start")
    assert started.status_code == 200
    assert started.json()["state"] == CameraState.RUNNING
    stopped = camera_client.post("/api/cameras/default/stop")
    assert stopped.status_code == 200
    assert stopped.json()["state"] == CameraState.CLOSED


def test_double_start_conflict(camera_client: TestClient) -> None:
    assert camera_client.post("/api/cameras/default/start").status_code == 200
    again = camera_client.post("/api/cameras/default/start")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "camera_already_running"
    camera_client.post("/api/cameras/default/stop")


def test_stop_when_not_running(camera_client: TestClient) -> None:
    response = camera_client.post("/api/cameras/default/stop")
    assert response.status_code == 409


def test_detections_when_disabled(camera_client: TestClient) -> None:
    response = camera_client.get("/api/cameras/default/detections")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["faces"] == []
