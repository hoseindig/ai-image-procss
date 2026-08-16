"""API schemas for face detection results. No NumPy or ONNX types."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.vision.types import BoundingBox, FaceLandmarks, TrackState


class FaceDetectionDto(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: BoundingBox
    landmarks: FaceLandmarks


class FaceTrackDto(BaseModel):
    track_id: int = Field(ge=1)
    state: TrackState
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: BoundingBox
    landmarks: FaceLandmarks
    age_frames: int = Field(ge=1)
    missed_frames: int = Field(ge=0)


class DetectionResponse(BaseModel):
    camera_id: str
    enabled: bool
    timestamp: datetime | None = None
    faces: list[FaceDetectionDto] = Field(default_factory=list)
    tracks: list[FaceTrackDto] = Field(default_factory=list)
    inference_ms: float | None = None
    tracking_ms: float | None = None
    error: str | None = None
