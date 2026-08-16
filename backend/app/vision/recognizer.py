"""Face recognition protocol. Independent of SFace / ONNX Runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.vision.embedder import FaceEmbedding
from app.vision.types import RecognitionReason, RecognitionStatus


@dataclass(frozen=True)
class RecognitionResult:
    """One recognition decision for a track. Track ID ≠ Person ID."""

    status: RecognitionStatus
    track_id: int
    person_id: str | None = None
    person_display_name: str | None = None
    similarity: float | None = None
    enrollment_id: str | None = None
    reason: RecognitionReason | None = None


class FaceRecognizer(Protocol):
    def recognize(self, embedding: FaceEmbedding) -> RecognitionResult:
        """Compare a query embedding to the gallery. No side effects on storage."""
        ...
