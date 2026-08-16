"""Face detection domain types. Coordinates are in the original frame."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Point(BaseModel):
    """Pixel coordinate. Origin is the top-left of the original frame."""

    x: float
    y: float


class BoundingBox(BaseModel):
    """Axis-aligned box in original-frame pixels. Origin is top-left."""

    x: float
    y: float
    width: float = Field(ge=0)
    height: float = Field(ge=0)


class FaceLandmarks(BaseModel):
    """Five YuNet landmarks in original-frame pixels.

    Left/right follow OpenCV YuNet naming (right eye, left eye, nose,
    right mouth corner, left mouth corner as produced by the model heads).
    """

    left_eye: Point
    right_eye: Point
    nose: Point
    left_mouth: Point
    right_mouth: Point


class FaceDetection(BaseModel):
    """One detected face. `confidence` is the YuNet detection score, not a probability."""

    bounding_box: BoundingBox
    confidence: float = Field(ge=0.0, le=1.0)
    landmarks: FaceLandmarks


class TrackState(StrEnum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    LOST = "lost"


class FaceTrack(BaseModel):
    """One tracked face. `track_id` is a temporary tracking ID, not a person ID."""

    track_id: int = Field(ge=1)
    bounding_box: BoundingBox
    confidence: float = Field(ge=0.0, le=1.0)
    landmarks: FaceLandmarks
    age_frames: int = Field(ge=1)
    missed_frames: int = Field(ge=0)
    state: TrackState


class QualityRejectionReason(StrEnum):
    """Structured rejection reasons. Engineering heuristics, not biometric scores."""

    FACE_TOO_SMALL = "face_too_small"
    TOO_BLURRY = "too_blurry"
    TOO_DARK = "too_dark"
    TOO_BRIGHT = "too_bright"
    INVALID_LANDMARKS = "invalid_landmarks"
    INVALID_CROP = "invalid_crop"


class FaceQuality(BaseModel):
    """Per-track quality assessment. `accepted` is a gate, not a probability."""

    track_id: int = Field(ge=1)
    accepted: bool
    reasons: list[QualityRejectionReason] = Field(default_factory=list)
    face_width: float = Field(ge=0.0)
    face_height: float = Field(ge=0.0)
    sharpness: float | None = None
    brightness: float | None = None
    landmarks_valid: bool


class EmbeddingStatus(StrEnum):
    GENERATED = "generated"
    SKIPPED = "skipped"
    FAILED = "failed"


class EmbeddingSkipReason(StrEnum):
    QUALITY_REJECTED = "quality_rejected"
    ALIGNMENT_UNAVAILABLE = "alignment_unavailable"
    EMBEDDING_DISABLED = "embedding_disabled"
    INFERENCE_FAILED = "inference_failed"


class EmbeddingInfo(BaseModel):
    """API-safe embedding metadata. Raw vectors are never included."""

    track_id: int = Field(ge=1)
    status: EmbeddingStatus
    dimension: int | None = Field(default=None, ge=1)
    reason: EmbeddingSkipReason | None = None
    normalized: bool = False


class DetectionSnapshot(BaseModel):
    """Latest completed detection for a camera. Replaced as a whole; never queued."""

    camera_id: str
    timestamp: datetime | None = None
    faces: list[FaceDetection] = Field(default_factory=list)
    tracks: list[FaceTrack] = Field(default_factory=list)
    qualities: list[FaceQuality] = Field(default_factory=list)
    embeddings: list[EmbeddingInfo] = Field(default_factory=list)
    inference_ms: float | None = None
    tracking_ms: float | None = None
    quality_ms: float | None = None
    alignment_ms: float | None = None
    embedding_ms: float | None = None
    aligned_count: int = Field(default=0, ge=0)
    aligned_track_ids: list[int] = Field(default_factory=list)
    embedded_count: int = Field(default=0, ge=0)
    error: str | None = None
