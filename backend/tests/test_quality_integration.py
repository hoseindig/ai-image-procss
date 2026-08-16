"""Integration: camera → detection → tracker → quality → alignment."""

from __future__ import annotations

import time

from app.cameras.manager import CameraManager
from app.cameras.types import CameraConfig, Frame
from app.core.config import Settings
from app.vision.runtime import DetectionRuntime
from app.vision.types import DetectionSnapshot, FaceDetection, QualityRejectionReason
from tests.fake_camera import FakeCameraSource
from tests.quality_helpers import textured_frame
from tests.yunet_helpers import sample_face


class LargeFaceDetector:
    provider = "test"

    def detect(self, frame: Frame) -> list[FaceDetection]:
        return [sample_face(x=40, y=40, width=100, height=100, confidence=0.93)]


class TinyFaceDetector:
    provider = "test"

    def detect(self, frame: Frame) -> list[FaceDetection]:
        return [sample_face(x=10, y=10, width=20, height=20, confidence=0.9)]


def test_pipeline_accepts_and_aligns_good_face(settings: Settings) -> None:
    manager = CameraManager(
        source_factory=lambda config: _TexturedFakeCamera(config, face_box=(40, 40, 100, 100))
    )
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=320, height=240, fps=10))
    enabled = settings.model_copy(
        update={
            "face_detection_enabled": True,
            "face_tracking_enabled": True,
            "face_quality_enabled": True,
            "face_alignment_enabled": True,
            "face_quality_min_face_width": 80,
            "face_quality_min_face_height": 80,
            "face_quality_min_sharpness": 60,
        }
    )
    runtime = DetectionRuntime(LargeFaceDetector(), enabled, manager)
    try:
        manager.start("cam-1")
        runtime.attach("cam-1")
        snapshot = _wait_for_quality(runtime, "cam-1")
        assert snapshot.qualities
        assert snapshot.qualities[0].accepted is True
        assert snapshot.aligned_count == 1
        assert snapshot.aligned_track_ids == [1]
        aligned = runtime.latest_aligned("cam-1")
        assert len(aligned) == 1
        assert aligned[0].image.shape == (
            enabled.face_alignment_height,
            enabled.face_alignment_width,
            3,
        )
        assert aligned[0].source_track_id == 1
    finally:
        runtime.shutdown()
        manager.shutdown()


def test_pipeline_rejects_small_face_without_alignment(settings: Settings) -> None:
    manager = CameraManager(
        source_factory=lambda config: _TexturedFakeCamera(config, face_box=(10, 10, 20, 20))
    )
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=160, height=120, fps=10))
    enabled = settings.model_copy(
        update={
            "face_detection_enabled": True,
            "face_tracking_enabled": True,
            "face_quality_enabled": True,
            "face_alignment_enabled": True,
            "face_quality_min_face_width": 80,
            "face_quality_min_face_height": 80,
        }
    )
    runtime = DetectionRuntime(TinyFaceDetector(), enabled, manager)
    try:
        manager.start("cam-1")
        runtime.attach("cam-1")
        snapshot = _wait_for_quality(runtime, "cam-1")
        assert snapshot.qualities
        assert snapshot.qualities[0].accepted is False
        assert QualityRejectionReason.FACE_TOO_SMALL in snapshot.qualities[0].reasons
        assert snapshot.aligned_count == 0
        assert runtime.latest_aligned("cam-1") == ()
    finally:
        runtime.shutdown()
        manager.shutdown()


def test_quality_disabled_skips_assessment(settings: Settings) -> None:
    manager = CameraManager(
        source_factory=lambda config: _TexturedFakeCamera(config, face_box=(40, 40, 100, 100))
    )
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=320, height=240, fps=10))
    enabled = settings.model_copy(
        update={
            "face_detection_enabled": True,
            "face_tracking_enabled": True,
            "face_quality_enabled": False,
            "face_alignment_enabled": False,
        }
    )
    runtime = DetectionRuntime(LargeFaceDetector(), enabled, manager)
    try:
        manager.start("cam-1")
        runtime.attach("cam-1")
        snapshot = _wait_for_tracks(runtime, "cam-1")
        assert snapshot.tracks
        assert snapshot.qualities == []
        assert snapshot.aligned_count == 0
        assert snapshot.quality_ms is None
        assert snapshot.alignment_ms is None
    finally:
        runtime.shutdown()
        manager.shutdown()


class _TexturedFakeCamera(FakeCameraSource):
    def __init__(self, config: CameraConfig, face_box: tuple[int, int, int, int]) -> None:
        super().__init__(config)
        self._face_box = face_box

    def read(self) -> Frame | None:
        frame = super().read()
        if frame is None:
            return None
        textured = textured_frame(frame.width, frame.height, face_box=self._face_box)
        return Frame(
            data=textured.data,
            timestamp=frame.timestamp,
            width=frame.width,
            height=frame.height,
        )


def _wait_for_quality(runtime: DetectionRuntime, camera_id: str) -> DetectionSnapshot:
    deadline = time.monotonic() + 2.0
    latest = runtime.latest(camera_id)
    while time.monotonic() < deadline:
        latest = runtime.latest(camera_id)
        if latest is not None and latest.qualities:
            return latest
        time.sleep(0.01)
    assert latest is not None
    return latest


def _wait_for_tracks(runtime: DetectionRuntime, camera_id: str) -> DetectionSnapshot:
    deadline = time.monotonic() + 2.0
    latest = runtime.latest(camera_id)
    while time.monotonic() < deadline:
        latest = runtime.latest(camera_id)
        if latest is not None and latest.tracks:
            return latest
        time.sleep(0.01)
    assert latest is not None
    return latest
