"""Latest-frame face detection worker.

The camera capture thread keeps only the newest frame. This worker polls that
slot on an interval, runs FaceDetector, and keeps only the newest result.
There is no frame queue.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import datetime

from app.cameras.exceptions import CameraError
from app.cameras.types import Frame
from app.core.logging import get_logger
from app.vision.detector import FaceDetector
from app.vision.slot import LatestValueSlot
from app.vision.types import DetectionSnapshot

logger = get_logger("app.vision")

_THREAD_JOIN_TIMEOUT_SECONDS = 5.0
_IDLE_SLEEP_SECONDS = 0.01
_ERROR_BACKOFF_SECONDS = 0.2

FrameGetter = Callable[[], Frame | None]


class DetectionWorker:
    """One detection loop for one camera. Not a daemon thread."""

    def __init__(
        self,
        camera_id: str,
        frame_getter: FrameGetter,
        detector: FaceDetector,
        *,
        interval_ms: int,
    ) -> None:
        self._camera_id = camera_id
        self._frame_getter = frame_getter
        self._detector = detector
        self._interval_s = max(interval_ms, 1) / 1000.0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._results = LatestValueSlot[DetectionSnapshot]()
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._results.clear()
            thread = threading.Thread(
                target=self._run,
                name=f"detect-{self._camera_id}",
                daemon=False,
            )
            self._thread = thread
            self._running = True
        thread.start()
        logger.info(
            "Detection worker started camera_id=%s interval_ms=%s",
            self._camera_id,
            int(self._interval_s * 1000),
        )

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._stop_event.set()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=_THREAD_JOIN_TIMEOUT_SECONDS)
            if thread.is_alive():
                logger.error("Detection worker did not stop in time camera_id=%s", self._camera_id)
        with self._lock:
            self._thread = None
            self._running = False
        logger.info("Detection worker stopped camera_id=%s", self._camera_id)

    def is_running(self) -> bool:
        return self._running

    def latest(self) -> DetectionSnapshot | None:
        return self._results.get()

    def _run(self) -> None:
        last_infer = 0.0
        last_frame_at: datetime | None = None
        while not self._stop_event.is_set():
            now = time.monotonic()
            remaining = self._interval_s - (now - last_infer)
            if remaining > 0:
                self._stop_event.wait(min(remaining, _IDLE_SLEEP_SECONDS))
                continue
            try:
                frame = self._frame_getter()
            except CameraError:
                break
            except Exception:
                logger.exception(
                    "Detection worker failed to read a frame camera_id=%s", self._camera_id
                )
                self._store_error("Failed to read camera frame")
                self._stop_event.wait(_ERROR_BACKOFF_SECONDS)
                continue
            if frame is None:
                self._stop_event.wait(_IDLE_SLEEP_SECONDS)
                continue
            if last_frame_at is not None and frame.timestamp == last_frame_at:
                self._stop_event.wait(_IDLE_SLEEP_SECONDS)
                continue
            started = time.perf_counter()
            try:
                faces = self._detector.detect(frame)
            except Exception as exc:
                logger.exception("Face detection failed camera_id=%s", self._camera_id)
                self._store_error(str(exc) or "Face detection failed")
                last_infer = time.monotonic()
                self._stop_event.wait(_ERROR_BACKOFF_SECONDS)
                continue
            inference_ms = (time.perf_counter() - started) * 1000.0
            last_infer = time.monotonic()
            last_frame_at = frame.timestamp
            self._results.put(
                DetectionSnapshot(
                    camera_id=self._camera_id,
                    timestamp=frame.timestamp,
                    faces=faces,
                    inference_ms=inference_ms,
                    error=None,
                )
            )
        logger.info("Detection loop exiting camera_id=%s", self._camera_id)

    def _store_error(self, message: str) -> None:
        self._results.put(
            DetectionSnapshot(
                camera_id=self._camera_id,
                timestamp=None,
                faces=[],
                inference_ms=None,
                error=message,
            )
        )
