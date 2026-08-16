from __future__ import annotations

import time

from app.cameras.manager import CameraManager
from app.cameras.types import CameraConfig
from app.core.config import Settings
from app.vision.runtime import DetectionRuntime
from app.vision.types import DetectionSnapshot
from tests.fake_camera import FakeCameraSource
from tests.fake_vision import FakeFaceDetector
from tests.helpers import IsolatedSettings
from tests.yunet_helpers import sample_face


def test_fake_camera_manager_detector_pipeline(settings: Settings) -> None:
    created: list[FakeCameraSource] = []

    def factory(config: CameraConfig) -> FakeCameraSource:
        source = FakeCameraSource(config)
        created.append(source)
        return source

    manager = CameraManager(source_factory=factory)
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=80, height=60, fps=10))
    detector = FakeFaceDetector([sample_face(x=10, y=12, width=20, height=24, confidence=0.88)])
    enabled = settings.model_copy(update={"face_detection_enabled": True})
    runtime = DetectionRuntime(detector, enabled, manager)
    try:
        manager.start("cam-1")
        runtime.attach("cam-1")
        snapshot = _wait_for_faces(runtime, "cam-1")
        assert snapshot is not None
        assert snapshot.camera_id == "cam-1"
        assert len(snapshot.faces) == 1
        assert snapshot.faces[0].confidence == 0.88
        assert snapshot.faces[0].bounding_box.x == 10
        assert created[0].is_running()
    finally:
        runtime.shutdown()
        manager.shutdown()
    assert created[0].get_status().state.value == "closed"


def test_runtime_does_not_start_when_detection_disabled() -> None:
    settings = IsolatedSettings(face_detection_enabled=False)
    manager = CameraManager(source_factory=lambda config: FakeCameraSource(config))
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=32, height=24, fps=5))
    runtime = DetectionRuntime(FakeFaceDetector(), settings, manager)
    manager.start("cam-1")
    runtime.attach("cam-1")
    assert runtime.enabled is False
    assert runtime.latest("cam-1") is None
    runtime.shutdown()
    manager.shutdown()


def _wait_for_faces(runtime: DetectionRuntime, camera_id: str) -> DetectionSnapshot | None:
    deadline = time.monotonic() + 2.0
    snapshot = runtime.latest(camera_id)
    while time.monotonic() < deadline:
        snapshot = runtime.latest(camera_id)
        if snapshot is not None and snapshot.faces:
            return snapshot
        time.sleep(0.01)
    return snapshot
