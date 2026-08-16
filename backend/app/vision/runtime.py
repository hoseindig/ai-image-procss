"""Process-wide detection workers keyed by camera_id. No global mutable camera state."""

from __future__ import annotations

import threading

from app.cameras.manager import CameraManager
from app.cameras.source import CameraSource
from app.cameras.types import Frame
from app.core.config import Settings
from app.core.logging import get_logger
from app.vision.align import AlignedFace
from app.vision.detector import FaceDetector
from app.vision.factory import (
    create_face_aligner,
    create_face_quality_assessor,
    create_face_tracker,
)
from app.vision.types import DetectionSnapshot
from app.vision.worker import DetectionWorker, FrameGetter

logger = get_logger("app.vision")


class DetectionRuntime:
    """Attaches a latest-frame detection worker to running cameras."""

    def __init__(
        self,
        detector: FaceDetector | None,
        settings: Settings,
        camera_manager: CameraManager,
    ) -> None:
        self._detector = detector
        self._settings = settings
        self._camera_manager = camera_manager
        self._lock = threading.RLock()
        self._workers: dict[str, DetectionWorker] = {}

    @property
    def enabled(self) -> bool:
        return self._settings.face_detection_enabled and self._detector is not None

    @property
    def model_loaded(self) -> bool:
        return self._detector is not None

    @property
    def provider(self) -> str | None:
        if self._detector is None:
            return None
        provider = getattr(self._detector, "provider", None)
        return provider if isinstance(provider, str) else None

    @property
    def tracking_enabled(self) -> bool:
        return self._settings.face_tracking_enabled

    @property
    def quality_enabled(self) -> bool:
        return self._settings.face_quality_enabled

    @property
    def alignment_enabled(self) -> bool:
        return self._settings.face_alignment_enabled

    def attach(self, camera_id: str) -> None:
        if not self.enabled or self._detector is None:
            return
        source = self._camera_manager.get_source(camera_id)
        with self._lock:
            existing = self._workers.get(camera_id)
            if existing is not None and existing.is_running():
                return
            if existing is not None:
                existing.stop()
            worker = DetectionWorker(
                camera_id,
                _frame_getter(source),
                self._detector,
                interval_ms=self._settings.face_detection_inference_interval_ms,
                tracker=create_face_tracker(self._settings),
                quality_assessor=create_face_quality_assessor(self._settings),
                aligner=create_face_aligner(self._settings),
            )
            self._workers[camera_id] = worker
        worker.start()

    def detach(self, camera_id: str) -> None:
        with self._lock:
            worker = self._workers.pop(camera_id, None)
        if worker is not None:
            worker.stop()

    def latest(self, camera_id: str) -> DetectionSnapshot | None:
        with self._lock:
            worker = self._workers.get(camera_id)
        if worker is None:
            return None
        return worker.latest()

    def latest_aligned(self, camera_id: str) -> tuple[AlignedFace, ...]:
        with self._lock:
            worker = self._workers.get(camera_id)
        if worker is None:
            return ()
        return worker.latest_aligned()

    def last_inference_ms(self) -> float | None:
        with self._lock:
            workers = list(self._workers.values())
        for worker in workers:
            snapshot = worker.latest()
            if snapshot is not None and snapshot.inference_ms is not None:
                return snapshot.inference_ms
        return None

    def shutdown(self) -> None:
        with self._lock:
            workers = list(self._workers.items())
            self._workers.clear()
        for camera_id, worker in workers:
            try:
                worker.stop()
            except Exception:
                logger.exception("Error stopping detection worker camera_id=%s", camera_id)


def _frame_getter(source: CameraSource) -> FrameGetter:
    def read() -> Frame | None:
        return source.read()

    return read
