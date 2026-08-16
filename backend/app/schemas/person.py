"""Pydantic schemas for person enrollment APIs. Raw vectors are write-only."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.persons.embedding_codec import EMBEDDING_DIM

DISPLAY_NAME_MAX_LENGTH = 100


class PersonCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=DISPLAY_NAME_MAX_LENGTH)

    @field_validator("display_name")
    @classmethod
    def strip_display_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("display_name must be non-empty after trimming")
        if len(trimmed) > DISPLAY_NAME_MAX_LENGTH:
            raise ValueError(f"display_name must be at most {DISPLAY_NAME_MAX_LENGTH} characters")
        return trimmed


class PersonUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=DISPLAY_NAME_MAX_LENGTH)
    active: bool | None = None

    @field_validator("display_name")
    @classmethod
    def strip_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("display_name must be non-empty after trimming")
        if len(trimmed) > DISPLAY_NAME_MAX_LENGTH:
            raise ValueError(f"display_name must be at most {DISPLAY_NAME_MAX_LENGTH} characters")
        return trimmed


class PersonResponse(BaseModel):
    id: str
    display_name: str
    active: bool
    created_at: datetime
    updated_at: datetime
    enrollment_count: int = 0


class PersonListResponse(BaseModel):
    persons: list[PersonResponse]


class EnrollmentQualityInput(BaseModel):
    """Quality gate payload. Enrollment requires accepted=true."""

    accepted: bool
    face_width: float | None = None
    face_height: float | None = None
    sharpness: float | None = None
    brightness: float | None = None


class EnrollmentCreateRequest(BaseModel):
    """Write-only embedding vector. Never returned by GET endpoints."""

    embedding: list[float] = Field(min_length=EMBEDDING_DIM, max_length=EMBEDDING_DIM)
    normalized: bool = True
    quality: EnrollmentQualityInput
    source_track_id: int | None = Field(default=None, ge=0)


class EnrollmentResponse(BaseModel):
    """Enrollment metadata only — no raw embedding vector."""

    id: str
    person_id: str
    dimension: int
    normalized: bool
    face_width: float | None = None
    face_height: float | None = None
    sharpness: float | None = None
    brightness: float | None = None
    source_track_id: int | None = None
    created_at: datetime


class EnrollmentListResponse(BaseModel):
    enrollments: list[EnrollmentResponse]
