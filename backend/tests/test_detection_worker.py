from __future__ import annotations

import time

from app.cameras.types import CameraConfig
from app.vision.exceptions import InferenceError
from app.vision.types import DetectionSnapshot
from app.vision.worker import DetectionWorker
from tests.fake_camera import FakeCameraSource
from tests.fake_vision import FakeFaceDetector
from tests.yunet_helpers import sample_face


def _source() -> FakeCameraSource:
    source = FakeCameraSource(
        CameraConfig(camera_id="cam-1", name="Fake", width=64, height=48, fps=10)
    )
    source.open()
    source.start()
    return source


def test_worker_open_start_read_stop_close() -> None:
    source = _source()
    detector = FakeFaceDetector([sample_face(x=4, y=4, width=16, height=16)])
    worker = DetectionWorker("cam-1", source.read, detector, interval_ms=10)
    try:
        worker.start()
        snapshot = _wait_for_snapshot(worker)
        assert snapshot is not None
        assert snapshot.camera_id == "cam-1"
        assert len(snapshot.faces) == 1
        assert snapshot.inference_ms is not None
        assert snapshot.error is None
    finally:
        worker.stop()
        source.stop()
        source.close()
    assert worker.is_running() is False
    assert source.close_count == 1


def test_worker_keeps_only_latest_result() -> None:
    source = _source()
    detector = FakeFaceDetector([sample_face(x=1, y=1, width=8, height=8)])
    worker = DetectionWorker("cam-1", source.read, detector, interval_ms=5)
    try:
        worker.start()
        _wait_for_snapshot(worker)
        detector.faces = [sample_face(x=20, y=20, width=8, height=8, confidence=0.81)]
        snapshot = _wait_for_snapshot(worker, expected_confidence=0.81)
        assert snapshot is not None
        assert len(snapshot.faces) == 1
        assert snapshot.faces[0].confidence == 0.81
    finally:
        worker.stop()
        source.close()


def test_worker_records_detector_errors_without_dying() -> None:
    source = _source()
    detector = FakeFaceDetector(error=InferenceError("boom"))
    worker = DetectionWorker("cam-1", source.read, detector, interval_ms=5)
    try:
        worker.start()
        snapshot = _wait_for_error(worker)
        assert snapshot is not None
        assert snapshot.error is not None
        assert "boom" in snapshot.error
        assert worker.is_running() is True
    finally:
        worker.stop()
        source.close()


def test_worker_stop_is_idempotent() -> None:
    source = _source()
    worker = DetectionWorker("cam-1", source.read, FakeFaceDetector(), interval_ms=20)
    worker.start()
    worker.stop()
    worker.stop()
    source.close()


def _wait_for_snapshot(
    worker: DetectionWorker, expected_confidence: float | None = None
) -> DetectionSnapshot | None:
    deadline = time.monotonic() + 2.0
    latest = worker.latest()
    while time.monotonic() < deadline:
        latest = worker.latest()
        if (
            latest is not None
            and latest.faces
            and (expected_confidence is None or latest.faces[0].confidence == expected_confidence)
        ):
            return latest
        time.sleep(0.01)
    return latest


def _wait_for_error(worker: DetectionWorker) -> DetectionSnapshot | None:
    deadline = time.monotonic() + 2.0
    latest = worker.latest()
    while time.monotonic() < deadline:
        latest = worker.latest()
        if latest is not None and latest.error:
            return latest
        time.sleep(0.01)
    return latest
