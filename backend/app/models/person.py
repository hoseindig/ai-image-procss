"""ORM models for persons and face enrollment samples."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.persons.embedding_codec import EMBEDDING_DIM


class Person(Base):
    """Persistent identity record. Track ID is never stored here."""

    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    enrollments: Mapped[list[EnrollmentSample]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by="EnrollmentSample.created_at",
    )


class EnrollmentSample(Base):
    """One gallery embedding for a person. No image/snapshot bytes."""

    __tablename__ = "enrollment_samples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False, default=EMBEDDING_DIM)
    normalized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    face_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    face_height: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpness: Mapped[float | None] = mapped_column(Float, nullable=True)
    brightness: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    person: Mapped[Person] = relationship(back_populates="enrollments")
