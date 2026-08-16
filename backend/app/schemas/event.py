"""Pydantic schemas for event APIs. No embeddings or images."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.events.types import EventType


class EventResponse(BaseModel):
    id: str
    event_type: EventType
    camera_id: str
    track_id: int = Field(ge=1)
    person_id: str | None = None
    enrollment_id: str | None = None
    similarity: float | None = None
    occurred_at: datetime
    created_at: datetime


class EventListResponse(BaseModel):
    items: list[EventResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
