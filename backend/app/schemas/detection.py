"""API schemas for face detection results. No NumPy or ONNX types."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.vision.types import (
    BoundingBox,
    EmbeddingSkipReason,
    EmbeddingStatus,
    FaceLandmarks,
    QualityRejectionReason,
    RecognitionReason,
    RecognitionStatus,
    TrackState,
)


class FaceDetectionDto(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: BoundingBox
    landmarks: FaceLandmarks


class FaceQualityDto(BaseModel):
    accepted: bool
    reasons: list[QualityRejectionReason] = Field(default_factory=list)
    face_width: float = Field(ge=0.0)
    face_height: float = Field(ge=0.0)
    sharpness: float | None = None
    brightness: float | None = None
    landmarks_valid: bool
    aligned: bool = False


class FaceEmbeddingDto(BaseModel):
    """Embedding metadata only. Raw vectors are never exposed on this API."""

    status: EmbeddingStatus
    dimension: int | None = Field(default=None, ge=1)
    reason: EmbeddingSkipReason | None = None
    normalized: bool = False


class FaceRecognitionDto(BaseModel):
    """Recognition metadata. Similarity is a score, not a probability/percentage."""

    status: RecognitionStatus
    person_id: str | None = None
    person_display_name: str | None = None
    similarity: float | None = None
    enrollment_id: str | None = None
    reason: RecognitionReason | None = None


class FaceTrackDto(BaseModel):
    track_id: int = Field(ge=1)
    state: TrackState
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: BoundingBox
    landmarks: FaceLandmarks
    age_frames: int = Field(ge=1)
    missed_frames: int = Field(ge=0)
    quality: FaceQualityDto | None = None
    embedding: FaceEmbeddingDto | None = None
    recognition: FaceRecognitionDto | None = None


class DetectionResponse(BaseModel):
    camera_id: str
    enabled: bool
    timestamp: datetime | None = None
    faces: list[FaceDetectionDto] = Field(default_factory=list)
    tracks: list[FaceTrackDto] = Field(default_factory=list)
    inference_ms: float | None = None
    tracking_ms: float | None = None
    quality_ms: float | None = None
    alignment_ms: float | None = None
    embedding_ms: float | None = None
    recognition_ms: float | None = None
    aligned_count: int = Field(default=0, ge=0)
    embedded_count: int = Field(default=0, ge=0)
    error: str | None = None
