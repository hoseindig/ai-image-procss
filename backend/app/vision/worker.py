"""Latest-frame face detection worker.

The camera capture thread keeps only the newest frame. This worker polls that
slot on an interval, runs FaceDetector → FaceTracker → quality → alignment,
and keeps only the newest result. There is no frame queue.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import datetime

from app.cameras.exceptions import CameraError
from app.cameras.types import Frame
from app.core.logging import get_logger
from app.vision.align import AlignedFace, FaceAligner
from app.vision.detector import FaceDetector
from app.vision.quality import FaceQualityAssessor
from app.vision.slot import LatestValueSlot
from app.vision.tracker import FaceTracker
from app.vision.types import DetectionSnapshot, FaceQuality, FaceTrack

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
        tracker: FaceTracker | None = None,
        quality_assessor: FaceQualityAssessor | None = None,
        aligner: FaceAligner | None = None,
    ) -> None:
        self._camera_id = camera_id
        self._frame_getter = frame_getter
        self._detector = detector
        self._tracker = tracker
        self._quality_assessor = quality_assessor
        self._aligner = aligner
        self._interval_s = max(interval_ms, 1) / 1000.0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._results = LatestValueSlot[DetectionSnapshot]()
        self._aligned = LatestValueSlot[tuple[AlignedFace, ...]]()
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._results.clear()
            self._aligned.clear()
            thread = threading.Thread(
                target=self._run,
                name=f"detect-{self._camera_id}",
                daemon=False,
            )
            self._thread = thread
            self._running = True
        thread.start()
        logger.info(
            "Detection worker started camera_id=%s interval_ms=%s tracking=%s "
            "quality=%s alignment=%s",
            self._camera_id,
            int(self._interval_s * 1000),
            self._tracker is not None,
            self._quality_assessor is not None,
            self._aligner is not None,
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
            self._aligned.clear()
        if self._tracker is not None:
            logger.info("Face tracker stopped camera_id=%s", self._camera_id)
        logger.info("Detection worker stopped camera_id=%s", self._camera_id)

    def is_running(self) -> bool:
        return self._running

    def latest(self) -> DetectionSnapshot | None:
        return self._results.get()

    def latest_aligned(self) -> tuple[AlignedFace, ...]:
        value = self._aligned.get()
        return value if value is not None else ()

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
            tracks: list[FaceTrack] = []
            tracking_ms: float | None = None
            if self._tracker is not None:
                track_started = time.perf_counter()
                try:
                    tracks = self._tracker.update(faces)
                except Exception as exc:
                    logger.exception("Face tracking failed camera_id=%s", self._camera_id)
                    self._store_error(str(exc) or "Face tracking failed")
                    last_infer = time.monotonic()
                    self._stop_event.wait(_ERROR_BACKOFF_SECONDS)
                    continue
                tracking_ms = (time.perf_counter() - track_started) * 1000.0

            qualities: list[FaceQuality] = []
            aligned: list[AlignedFace] = []
            quality_ms: float | None = None
            alignment_ms: float | None = None
            if self._quality_assessor is not None or self._aligner is not None:
                try:
                    qualities, aligned, quality_ms, alignment_ms = self._post_track(frame, tracks)
                except Exception as exc:
                    logger.exception("Face quality/alignment failed camera_id=%s", self._camera_id)
                    self._store_error(str(exc) or "Face quality/alignment failed")
                    last_infer = time.monotonic()
                    self._stop_event.wait(_ERROR_BACKOFF_SECONDS)
                    continue

            last_infer = time.monotonic()
            last_frame_at = frame.timestamp
            aligned_tuple = tuple(aligned)
            aligned_ids = [item.source_track_id for item in aligned_tuple]
            self._aligned.put(aligned_tuple)
            self._results.put(
                DetectionSnapshot(
                    camera_id=self._camera_id,
                    timestamp=frame.timestamp,
                    faces=faces,
                    tracks=tracks,
                    qualities=qualities,
                    inference_ms=inference_ms,
                    tracking_ms=tracking_ms,
                    quality_ms=quality_ms,
                    alignment_ms=alignment_ms,
                    aligned_count=len(aligned_tuple),
                    aligned_track_ids=aligned_ids,
                    error=None,
                )
            )
        logger.info("Detection loop exiting camera_id=%s", self._camera_id)

    def _post_track(
        self,
        frame: Frame,
        tracks: list[FaceTrack],
    ) -> tuple[list[FaceQuality], list[AlignedFace], float | None, float | None]:
        qualities: list[FaceQuality] = []
        aligned: list[AlignedFace] = []
        quality_ms: float | None = None
        alignment_ms: float | None = None

        current_tracks = [track for track in tracks if track.missed_frames == 0]

        if self._quality_assessor is not None:
            quality_started = time.perf_counter()
            for track in current_tracks:
                qualities.append(self._quality_assessor.assess(frame, track))
            quality_ms = (time.perf_counter() - quality_started) * 1000.0
            accepted_ids = {item.track_id for item in qualities if item.accepted}
            align_candidates = [track for track in current_tracks if track.track_id in accepted_ids]
        else:
            align_candidates = current_tracks

        if self._aligner is not None and align_candidates:
            align_started = time.perf_counter()
            for track in align_candidates:
                aligned.append(self._aligner.align(frame, track))
            alignment_ms = (time.perf_counter() - align_started) * 1000.0

        return qualities, aligned, quality_ms, alignment_ms

    def _store_error(self, message: str) -> None:
        self._aligned.put(())
        self._results.put(
            DetectionSnapshot(
                camera_id=self._camera_id,
                timestamp=None,
                faces=[],
                tracks=[],
                qualities=[],
                inference_ms=None,
                tracking_ms=None,
                quality_ms=None,
                alignment_ms=None,
                aligned_count=0,
                aligned_track_ids=[],
                error=message,
            )
        )
