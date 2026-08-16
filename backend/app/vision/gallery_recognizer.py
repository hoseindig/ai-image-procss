"""Gallery-backed face recognition (CPU, cosine similarity). No FAISS / vector DB."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from app.core.logging import get_logger
from app.persons.embedding_codec import validate_embedding_values
from app.persons.exceptions import InvalidEmbeddingError
from app.vision.embedder import FaceEmbedding
from app.vision.recognizer import RecognitionResult
from app.vision.similarity import cosine_similarity
from app.vision.types import RecognitionReason, RecognitionStatus

logger = get_logger("app.vision")

# OpenCV FaceRecognizerSF tutorial (DNN Face, LFW): cosine threshold 0.363 with
# FR_COSINE after L2-normalization in match(). Match when score >= threshold.
# This is an initial engineering default — not production biometric validation.
DEFAULT_RECOGNITION_THRESHOLD = 0.363


@dataclass(frozen=True)
class GalleryEntry:
    person_id: str
    display_name: str
    enrollment_id: str
    vector: NDArray[np.float32]


class GalleryStore(Protocol):
    def load_active_entries(self) -> list[GalleryEntry]:
        """Return enrollment vectors for active persons only."""
        ...


class InMemoryGalleryStore:
    """Deterministic gallery for unit tests and benchmarks."""

    def __init__(self, entries: list[GalleryEntry] | None = None) -> None:
        self._entries = list(entries or [])

    def load_active_entries(self) -> list[GalleryEntry]:
        return list(self._entries)

    def replace(self, entries: list[GalleryEntry]) -> None:
        self._entries = list(entries)


class GalleryFaceRecognizer:
    """FaceRecognizer that scans enrollment samples and picks the best person score.

    Per person: max similarity across that person's samples (no averaging).
    Global: person with the highest person score; match iff score >= threshold.
    """

    def __init__(
        self,
        gallery: GalleryStore,
        *,
        threshold: float = DEFAULT_RECOGNITION_THRESHOLD,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Recognition threshold must be in [0.0, 1.0]")
        self._gallery = gallery
        self._threshold = threshold

    @property
    def threshold(self) -> float:
        return self._threshold

    def recognize(self, embedding: FaceEmbedding) -> RecognitionResult:
        track_id = embedding.source_track_id
        try:
            query = validate_embedding_values(embedding.vector)
        except InvalidEmbeddingError:
            logger.warning(
                "Recognition rejected invalid embedding track_id=%s",
                track_id,
            )
            return RecognitionResult(
                status=RecognitionStatus.ERROR,
                track_id=track_id,
                reason=RecognitionReason.INVALID_EMBEDDING,
            )

        try:
            entries = self._gallery.load_active_entries()
        except Exception:
            logger.exception("Gallery load failed track_id=%s", track_id)
            return RecognitionResult(
                status=RecognitionStatus.ERROR,
                track_id=track_id,
                reason=RecognitionReason.INTERNAL_ERROR,
            )

        if not entries:
            return RecognitionResult(
                status=RecognitionStatus.UNKNOWN,
                track_id=track_id,
                reason=RecognitionReason.GALLERY_EMPTY,
            )

        # person_id -> (best_similarity, enrollment_id, display_name)
        best_by_person: dict[str, tuple[float, str, str]] = {}
        for entry in entries:
            try:
                score = cosine_similarity(query, entry.vector)
            except InvalidEmbeddingError:
                logger.warning(
                    "Skipping corrupt gallery sample enrollment_id=%s",
                    entry.enrollment_id,
                )
                continue
            current = best_by_person.get(entry.person_id)
            if current is None or score > current[0]:
                best_by_person[entry.person_id] = (
                    score,
                    entry.enrollment_id,
                    entry.display_name,
                )

        if not best_by_person:
            return RecognitionResult(
                status=RecognitionStatus.UNKNOWN,
                track_id=track_id,
                reason=RecognitionReason.GALLERY_EMPTY,
            )

        best_person_id, (best_score, best_enrollment_id, best_name) = max(
            best_by_person.items(),
            key=lambda item: item[1][0],
        )

        # Boundary: matched when similarity >= threshold (OpenCV FR_COSINE convention).
        if best_score >= self._threshold:
            # Per-frame match details stay at DEBUG to avoid log floods.
            logger.debug(
                "Recognition matched track_id=%s person_id=%s enrollment_id=%s "
                "similarity=%.6f threshold=%.6f",
                track_id,
                best_person_id,
                best_enrollment_id,
                best_score,
                self._threshold,
            )
            return RecognitionResult(
                status=RecognitionStatus.MATCHED,
                track_id=track_id,
                person_id=best_person_id,
                person_display_name=best_name,
                similarity=best_score,
                enrollment_id=best_enrollment_id,
            )

        logger.debug(
            "Recognition unknown track_id=%s similarity=%.6f threshold=%.6f reason=%s",
            track_id,
            best_score,
            self._threshold,
            RecognitionReason.BELOW_THRESHOLD.value,
        )
        return RecognitionResult(
            status=RecognitionStatus.UNKNOWN,
            track_id=track_id,
            similarity=best_score,
            reason=RecognitionReason.BELOW_THRESHOLD,
        )


def skipped_recognition(
    track_id: int,
    reason: RecognitionReason,
) -> RecognitionResult:
    return RecognitionResult(
        status=RecognitionStatus.SKIPPED,
        track_id=track_id,
        reason=reason,
    )
