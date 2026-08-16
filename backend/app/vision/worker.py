"""Latest-frame face detection worker.

The camera capture thread keeps only the newest frame. This worker polls that
slot on an interval, runs FaceDetector → FaceTracker → quality → alignment →
embedding → recognition, and keeps only the newest result. There is no frame queue.
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
from app.vision.embedder import FaceEmbedder, FaceEmbedding
from app.vision.gallery_recognizer import skipped_recognition
from app.vision.quality import FaceQualityAssessor
from app.vision.recognizer import FaceRecognizer, RecognitionResult
from app.vision.slot import LatestValueSlot
from app.vision.tracker import FaceTracker
from app.vision.types import (
    DetectionSnapshot,
    EmbeddingInfo,
    EmbeddingSkipReason,
    EmbeddingStatus,
    FaceQuality,
    FaceTrack,
    RecognitionInfo,
    RecognitionReason,
    RecognitionStatus,
)

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
        embedder: FaceEmbedder | None = None,
        recognizer: FaceRecognizer | None = None,
    ) -> None:
        self._camera_id = camera_id
        self._frame_getter = frame_getter
        self._detector = detector
        self._tracker = tracker
        self._quality_assessor = quality_assessor
        self._aligner = aligner
        self._embedder = embedder
        self._recognizer = recognizer
        self._interval_s = max(interval_ms, 1) / 1000.0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._results = LatestValueSlot[DetectionSnapshot]()
        self._aligned = LatestValueSlot[tuple[AlignedFace, ...]]()
        self._embeddings = LatestValueSlot[tuple[FaceEmbedding, ...]]()
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._results.clear()
            self._aligned.clear()
            self._embeddings.clear()
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
            "quality=%s alignment=%s embedding=%s recognition=%s",
            self._camera_id,
            int(self._interval_s * 1000),
            self._tracker is not None,
            self._quality_assessor is not None,
            self._aligner is not None,
            self._embedder is not None,
            self._recognizer is not None,
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
            self._embeddings.clear()
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

    def latest_embeddings(self) -> tuple[FaceEmbedding, ...]:
        value = self._embeddings.get()
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
            embedding_infos: list[EmbeddingInfo] = []
            embeddings: list[FaceEmbedding] = []
            recognitions: list[RecognitionInfo] = []
            quality_ms: float | None = None
            alignment_ms: float | None = None
            embedding_ms: float | None = None
            recognition_ms: float | None = None
            if (
                self._quality_assessor is not None
                or self._aligner is not None
                or self._embedder is not None
                or self._recognizer is not None
            ):
                try:
                    (
                        qualities,
                        aligned,
                        embedding_infos,
                        embeddings,
                        recognitions,
                        quality_ms,
                        alignment_ms,
                        embedding_ms,
                        recognition_ms,
                    ) = self._post_track(frame, tracks)
                except Exception as exc:
                    logger.exception(
                        "Face quality/alignment/embedding/recognition failed camera_id=%s",
                        self._camera_id,
                    )
                    self._store_error(
                        str(exc) or "Face quality/alignment/embedding/recognition failed"
                    )
                    last_infer = time.monotonic()
                    self._stop_event.wait(_ERROR_BACKOFF_SECONDS)
                    continue

            last_infer = time.monotonic()
            last_frame_at = frame.timestamp
            aligned_tuple = tuple(aligned)
            embedding_tuple = tuple(embeddings)
            aligned_ids = [item.source_track_id for item in aligned_tuple]
            self._aligned.put(aligned_tuple)
            self._embeddings.put(embedding_tuple)
            self._results.put(
                DetectionSnapshot(
                    camera_id=self._camera_id,
                    timestamp=frame.timestamp,
                    faces=faces,
                    tracks=tracks,
                    qualities=qualities,
                    embeddings=embedding_infos,
                    recognitions=recognitions,
                    inference_ms=inference_ms,
                    tracking_ms=tracking_ms,
                    quality_ms=quality_ms,
                    alignment_ms=alignment_ms,
                    embedding_ms=embedding_ms,
                    recognition_ms=recognition_ms,
                    aligned_count=len(aligned_tuple),
                    aligned_track_ids=aligned_ids,
                    embedded_count=len(embedding_tuple),
                    error=None,
                )
            )
        logger.info("Detection loop exiting camera_id=%s", self._camera_id)

    def _post_track(
        self,
        frame: Frame,
        tracks: list[FaceTrack],
    ) -> tuple[
        list[FaceQuality],
        list[AlignedFace],
        list[EmbeddingInfo],
        list[FaceEmbedding],
        list[RecognitionInfo],
        float | None,
        float | None,
        float | None,
        float | None,
    ]:
        qualities: list[FaceQuality] = []
        aligned: list[AlignedFace] = []
        embedding_infos: list[EmbeddingInfo] = []
        embeddings: list[FaceEmbedding] = []
        recognitions: list[RecognitionInfo] = []
        quality_ms: float | None = None
        alignment_ms: float | None = None
        embedding_ms: float | None = None
        recognition_ms: float | None = None

        current_tracks = [track for track in tracks if track.missed_frames == 0]

        if self._quality_assessor is not None:
            quality_started = time.perf_counter()
            for track in current_tracks:
                qualities.append(self._quality_assessor.assess(frame, track))
            quality_ms = (time.perf_counter() - quality_started) * 1000.0
            accepted_ids = {item.track_id for item in qualities if item.accepted}
            align_candidates = [track for track in current_tracks if track.track_id in accepted_ids]
            rejected_ids = {item.track_id for item in qualities if not item.accepted}
        else:
            align_candidates = list(current_tracks)
            rejected_ids = set()

        if self._aligner is not None and align_candidates:
            align_started = time.perf_counter()
            for track in align_candidates:
                aligned.append(self._aligner.align(frame, track))
            alignment_ms = (time.perf_counter() - align_started) * 1000.0

        aligned_by_id = {item.source_track_id: item for item in aligned}
        embedding_by_track: dict[int, FaceEmbedding] = {}

        if self._embedder is not None:
            embed_started = time.perf_counter()
            for track in current_tracks:
                if track.track_id in rejected_ids:
                    embedding_infos.append(
                        EmbeddingInfo(
                            track_id=track.track_id,
                            status=EmbeddingStatus.SKIPPED,
                            reason=EmbeddingSkipReason.QUALITY_REJECTED,
                        )
                    )
                    continue
                aligned_face = aligned_by_id.get(track.track_id)
                if aligned_face is None:
                    embedding_infos.append(
                        EmbeddingInfo(
                            track_id=track.track_id,
                            status=EmbeddingStatus.SKIPPED,
                            reason=EmbeddingSkipReason.ALIGNMENT_UNAVAILABLE,
                        )
                    )
                    continue
                try:
                    embedding = self._embedder.embed(aligned_face)
                except Exception as exc:
                    logger.exception(
                        "Face embedding failed camera_id=%s track_id=%s",
                        self._camera_id,
                        track.track_id,
                    )
                    embedding_infos.append(
                        EmbeddingInfo(
                            track_id=track.track_id,
                            status=EmbeddingStatus.FAILED,
                            reason=EmbeddingSkipReason.INFERENCE_FAILED,
                        )
                    )
                    _ = exc
                    continue
                embeddings.append(embedding)
                embedding_by_track[track.track_id] = embedding
                embedding_infos.append(
                    EmbeddingInfo(
                        track_id=track.track_id,
                        status=EmbeddingStatus.GENERATED,
                        dimension=embedding.dimension,
                        normalized=embedding.normalized,
                    )
                )
            if embeddings or embedding_infos:
                embedding_ms = (time.perf_counter() - embed_started) * 1000.0

        if self._recognizer is not None:
            recog_started = time.perf_counter()
            for track in current_tracks:
                result = self._recognize_track(
                    track.track_id,
                    rejected_ids=rejected_ids,
                    aligned_by_id=aligned_by_id,
                    embedding_by_track=embedding_by_track,
                    embedding_infos=embedding_infos,
                )
                recognitions.append(_recognition_info(result))
            if recognitions:
                recognition_ms = (time.perf_counter() - recog_started) * 1000.0

        return (
            qualities,
            aligned,
            embedding_infos,
            embeddings,
            recognitions,
            quality_ms,
            alignment_ms,
            embedding_ms,
            recognition_ms,
        )

    def _recognize_track(
        self,
        track_id: int,
        *,
        rejected_ids: set[int],
        aligned_by_id: dict[int, AlignedFace],
        embedding_by_track: dict[int, FaceEmbedding],
        embedding_infos: list[EmbeddingInfo],
    ) -> RecognitionResult:
        assert self._recognizer is not None
        if track_id in rejected_ids:
            return skipped_recognition(track_id, RecognitionReason.QUALITY_REJECTED)
        if track_id not in aligned_by_id and self._aligner is not None:
            return skipped_recognition(track_id, RecognitionReason.ALIGNMENT_UNAVAILABLE)
        embedding = embedding_by_track.get(track_id)
        if embedding is None:
            failed = any(
                item.track_id == track_id and item.status is EmbeddingStatus.FAILED
                for item in embedding_infos
            )
            if failed:
                return skipped_recognition(track_id, RecognitionReason.EMBEDDING_FAILED)
            return skipped_recognition(track_id, RecognitionReason.EMBEDDING_UNAVAILABLE)
        try:
            return self._recognizer.recognize(embedding)
        except Exception:
            logger.exception(
                "Face recognition failed camera_id=%s track_id=%s",
                self._camera_id,
                track_id,
            )
            return RecognitionResult(
                status=RecognitionStatus.ERROR,
                track_id=track_id,
                reason=RecognitionReason.INTERNAL_ERROR,
            )

    def _store_error(self, message: str) -> None:
        self._aligned.put(())
        self._embeddings.put(())
        self._results.put(
            DetectionSnapshot(
                camera_id=self._camera_id,
                timestamp=None,
                faces=[],
                tracks=[],
                qualities=[],
                embeddings=[],
                recognitions=[],
                inference_ms=None,
                tracking_ms=None,
                quality_ms=None,
                alignment_ms=None,
                embedding_ms=None,
                recognition_ms=None,
                aligned_count=0,
                aligned_track_ids=[],
                embedded_count=0,
                error=message,
            )
        )


def _recognition_info(result: RecognitionResult) -> RecognitionInfo:
    return RecognitionInfo(
        track_id=result.track_id,
        status=result.status,
        person_id=result.person_id,
        person_display_name=result.person_display_name,
        similarity=result.similarity,
        enrollment_id=result.enrollment_id,
        reason=result.reason,
    )
