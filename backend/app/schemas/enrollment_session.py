"""Pydantic schemas for camera enrollment sessions. No embedding vectors."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.persons.enrollment_session import EnrollmentSessionState
from app.vision.types import QualityRejectionReason


class EnrollmentSessionCreateRequest(BaseModel):
    camera_id: str | None = Field(
        default=None,
        min_length=1,
        description="Camera to enroll from. Defaults to the configured default camera.",
    )


class EnrollmentSessionResponse(BaseModel):
    id: str
    person_id: str
    camera_id: str
    state: EnrollmentSessionState
    track_id: int | None = None
    quality_reasons: list[QualityRejectionReason] = Field(default_factory=list)
    message: str | None = None
    error_code: str | None = None
    enrollment_id: str | None = None
    face_width: float | None = None
    face_height: float | None = None
    sharpness: float | None = None
    brightness: float | None = None
    created_at: datetime
    updated_at: datetime
