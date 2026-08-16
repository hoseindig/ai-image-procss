"""Face detection domain types. Coordinates are in the original frame."""

from __future__ import annotations

from datetime import datetime

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


class DetectionSnapshot(BaseModel):
    """Latest completed detection for a camera. Replaced as a whole; never queued."""

    camera_id: str
    timestamp: datetime | None = None
    faces: list[FaceDetection] = Field(default_factory=list)
    inference_ms: float | None = None
    error: str | None = None
