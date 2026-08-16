"""TEST ONLY schemas for recognition test harness. Never include embeddings."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RecognitionTestResponse(BaseModel):
    """Safe recognition test response (no embeddings / no image bytes)."""

    model_config = ConfigDict(extra="forbid")

    test_only: bool = Field(default=True, description="Always true — TEST ONLY endpoint")
    status: str
    track_id: int
    person_id: str | None = None
    person_display_name: str | None = None
    similarity: float | None = None
    enrollment_id: str | None = None
    reason: str | None = None
    event_id: str | None = None
    event_created: bool
    camera_id: str
    threshold: float
