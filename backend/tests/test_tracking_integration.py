from __future__ import annotations

import time

from app.cameras.manager import CameraManager
from app.cameras.types import CameraConfig, Frame
from app.core.config import Settings
from app.vision.runtime import DetectionRuntime
from app.vision.types import DetectionSnapshot, FaceDetection, TrackState
from tests.fake_camera import FakeCameraSource
from tests.yunet_helpers import sample_face


class MovingFaceDetector:
    provider = "test"

    def __init__(self) -> None:
        self.calls = 0

    def detect(self, frame: Frame) -> list[FaceDetection]:
        self.calls += 1
        x = 8.0 + float(self.calls) * 3.0
        return [sample_face(x=x, y=10, width=20, height=22, confidence=0.9)]


def test_moving_face_keeps_track_id(settings: Settings) -> None:
    manager = CameraManager(source_factory=lambda config: FakeCameraSource(config))
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=80, height=60, fps=10))
    detector = MovingFaceDetector()
    enabled = settings.model_copy(
        update={"face_detection_enabled": True, "face_tracking_enabled": True}
    )
    runtime = DetectionRuntime(detector, enabled, manager)
    try:
        manager.start("cam-1")
        runtime.attach("cam-1")
        snapshots = _wait_for_track_snapshots(runtime, "cam-1", count=3)
        ids = [item.tracks[0].track_id for item in snapshots]
        assert ids == [1, 1, 1]
        xs = [item.tracks[0].bounding_box.x for item in snapshots]
        assert xs[0] < xs[-1]
        assert snapshots[-1].tracks[0].state in {TrackState.TENTATIVE, TrackState.CONFIRMED}
    finally:
        runtime.shutdown()
        manager.shutdown()


def _wait_for_track_snapshots(
    runtime: DetectionRuntime, camera_id: str, count: int
) -> list[DetectionSnapshot]:
    deadline = time.monotonic() + 2.0
    seen: list[DetectionSnapshot] = []
    last_ts = None
    while time.monotonic() < deadline and len(seen) < count:
        snapshot = runtime.latest(camera_id)
        if (
            snapshot is not None
            and snapshot.tracks
            and snapshot.timestamp is not None
            and snapshot.timestamp != last_ts
        ):
            seen.append(snapshot)
            last_ts = snapshot.timestamp
        time.sleep(0.01)
    assert len(seen) >= count
    return seen
