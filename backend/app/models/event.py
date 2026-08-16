"""ORM model for recognition audit events. No embeddings or images."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Event(Base):
    """One persisted recognition/audit event. Track ID is runtime-only."""

    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_occurred_at", "occurred_at"),
        Index("ix_events_camera_occurred", "camera_id", "occurred_at"),
        Index("ix_events_person_occurred", "person_id", "occurred_at"),
        Index("ix_events_type_occurred", "event_type", "occurred_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False)
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)
    person_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    enrollment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
