"""TEST ONLY recognition harness (no webcam).

Disabled unless Settings.recognition_test_mode is True
(env RECOGNITION_TEST_MODE=false by default).

Reuses production SFace embedder, gallery recognizer, threshold, and EventService.
Does not return or log raw embeddings. Does not persist images or embeddings.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from app.services.event import EventService
from app.vision.align import AlignedFace
from app.vision.embedder import FaceEmbedder, FaceEmbedding
from app.vision.recognizer import FaceRecognizer, RecognitionResult


class RecognitionTestDisabledError(RuntimeError):
    """Raised when RECOGNITION_TEST_MODE is false."""

    def __init__(self) -> None:
        super().__init__(
            "Recognition test mode is disabled "
            "(set RECOGNITION_TEST_MODE=true only for local tests)"
        )


class RecognitionTestInputError(ValueError):
    """Invalid test image / crop for the TEST ONLY path."""


@dataclass(frozen=True)
class RecognitionTestOutcome:
    """Recognition (+ optional event) result. Never includes embeddings."""

    status: str
    track_id: int
    person_id: str | None
    person_display_name: str | None
    similarity: float | None
    enrollment_id: str | None
    reason: str | None
    event_id: str | None
    event_created: bool
    camera_id: str
    threshold: float


class RecognitionTestService:
    """TEST ONLY: aligned crop → real SFace → gallery → events.

    Webcam / DetectionWorker path is unchanged.
    """

    def __init__(
        self,
        *,
        enabled: bool,
        embedder: FaceEmbedder,
        recognizer: FaceRecognizer,
        event_service: EventService,
        recognition_threshold: float,
    ) -> None:
        self._enabled = enabled
        self._embedder = embedder
        self._recognizer = recognizer
        self._event_service = event_service
        self._threshold = recognition_threshold

    @property
    def enabled(self) -> bool:
        return self._enabled

    def require_enabled(self) -> None:
        if not self._enabled:
            raise RecognitionTestDisabledError()

    def recognize_aligned_bgr(
        self,
        image_bgr: NDArray[np.uint8],
        *,
        camera_id: str = "test",
        track_id: int = 1,
        record_event: bool = True,
    ) -> RecognitionTestOutcome:
        """Run real embed → recognize → optional event. TEST ONLY."""
        self.require_enabled()
        face = self._as_aligned_face(image_bgr, track_id=track_id)
        embedding = self._embedder.embed(face)
        # FaceEmbedding stays local; never logged or returned.
        result = self._recognize(embedding, track_id=track_id)
        return self._to_outcome(
            result,
            camera_id=camera_id,
            record_event=record_event,
        )

    def recognize_image_bytes(
        self,
        data: bytes,
        *,
        camera_id: str = "test",
        track_id: int = 1,
        record_event: bool = True,
    ) -> RecognitionTestOutcome:
        """Decode PNG/JPEG bytes as an aligned 112×112 BGR crop. TEST ONLY."""
        self.require_enabled()
        image = self._decode_aligned_crop(data)
        return self.recognize_aligned_bgr(
            image,
            camera_id=camera_id,
            track_id=track_id,
            record_event=record_event,
        )

    def _recognize(self, embedding: FaceEmbedding, *, track_id: int) -> RecognitionResult:
        # Ensure track_id on the embedding matches the requested test track.
        tagged = FaceEmbedding(
            vector=embedding.vector,
            dimension=embedding.dimension,
            source_track_id=track_id,
            normalized=embedding.normalized,
        )
        return self._recognizer.recognize(tagged)

    def _to_outcome(
        self,
        result: RecognitionResult,
        *,
        camera_id: str,
        record_event: bool,
    ) -> RecognitionTestOutcome:
        event_id: str | None = None
        event_created = False
        if record_event:
            record = self._event_service.record_from_recognition(camera_id, result)
            if record is not None:
                event_id = record.id
                event_created = True
        reason = result.reason.value if result.reason is not None else None
        return RecognitionTestOutcome(
            status=result.status.value,
            track_id=result.track_id,
            person_id=result.person_id,
            person_display_name=result.person_display_name,
            similarity=result.similarity,
            enrollment_id=result.enrollment_id,
            reason=reason,
            event_id=event_id,
            event_created=event_created,
            camera_id=camera_id,
            threshold=self._threshold,
        )

    @staticmethod
    def _as_aligned_face(image_bgr: NDArray[np.uint8], *, track_id: int) -> AlignedFace:
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise RecognitionTestInputError("Aligned crop must be HxWx3 BGR uint8")
        if image_bgr.dtype != np.uint8:
            raise RecognitionTestInputError("Aligned crop must be uint8")
        height, width = int(image_bgr.shape[0]), int(image_bgr.shape[1])
        if width != 112 or height != 112:
            raise RecognitionTestInputError(
                "TEST ONLY path expects a pre-aligned 112×112 BGR crop "
                "(synthetic fixtures or aligned face crops)"
            )
        return AlignedFace(
            image=np.ascontiguousarray(image_bgr),
            width=112,
            height=112,
            source_track_id=track_id,
            transform=np.eye(2, 3, dtype=np.float64),
        )

    @staticmethod
    def _decode_aligned_crop(data: bytes) -> NDArray[np.uint8]:
        if not data:
            raise RecognitionTestInputError("Empty image payload")
        arr = np.frombuffer(data, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            raise RecognitionTestInputError("Could not decode image (use PNG or JPEG)")
        typed: NDArray[np.uint8] = np.ascontiguousarray(image)
        return typed
