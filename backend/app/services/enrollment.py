"""Enrollment gallery persistence. Independent of SFace implementation."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.person import EnrollmentSample, Person
from app.persons.embedding_codec import (
    EMBEDDING_DIM,
    deserialize_embedding,
    serialize_embedding,
    validate_embedding_values,
)
from app.persons.exceptions import (
    EnrollmentNotFoundError,
    EnrollmentQualityRejectedError,
    PersonInactiveError,
    PersonNotFoundError,
)
from app.schemas.person import EnrollmentResponse

logger = get_logger("app.persons")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _to_response(sample: EnrollmentSample) -> EnrollmentResponse:
    return EnrollmentResponse(
        id=sample.id,
        person_id=sample.person_id,
        dimension=sample.dimension,
        normalized=sample.normalized,
        face_width=sample.face_width,
        face_height=sample.face_height,
        sharpness=sample.sharpness,
        brightness=sample.brightness,
        source_track_id=sample.source_track_id,
        created_at=sample.created_at,
    )


class EnrollmentService:
    """Stores validated embeddings for persons. Does not run recognition."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_embedding(
        self,
        person_id: str,
        embedding: Sequence[float],
        *,
        quality_accepted: bool,
        normalized: bool = True,
        face_width: float | None = None,
        face_height: float | None = None,
        sharpness: float | None = None,
        brightness: float | None = None,
        source_track_id: int | None = None,
    ) -> EnrollmentResponse:
        if not quality_accepted:
            raise EnrollmentQualityRejectedError()
        person = self._session.get(Person, person_id)
        if person is None:
            raise PersonNotFoundError(person_id)
        if not person.active:
            raise PersonInactiveError(person_id)

        # Validate before serialize; reject wrong dims / NaN / Inf explicitly.
        validate_embedding_values(embedding)
        blob = serialize_embedding(embedding)

        sample = EnrollmentSample(
            id=str(uuid4()),
            person_id=person_id,
            embedding=blob,
            dimension=EMBEDDING_DIM,
            normalized=normalized,
            face_width=face_width,
            face_height=face_height,
            sharpness=sharpness,
            brightness=brightness,
            source_track_id=source_track_id,
            created_at=_utc_now(),
        )
        self._session.add(sample)
        person.updated_at = _utc_now()
        self._session.commit()
        self._session.refresh(sample)
        logger.info(
            "Enrollment created person_id=%s enrollment_id=%s dimension=%s",
            person_id,
            sample.id,
            sample.dimension,
        )
        return _to_response(sample)

    def list_enrollments(self, person_id: str) -> list[EnrollmentResponse]:
        self._require_person(person_id)
        rows = self._session.scalars(
            select(EnrollmentSample)
            .where(EnrollmentSample.person_id == person_id)
            .order_by(EnrollmentSample.created_at.asc())
        ).all()
        return [_to_response(row) for row in rows]

    def get_enrollment(self, person_id: str, enrollment_id: str) -> EnrollmentResponse:
        sample = self._get_sample(person_id, enrollment_id)
        return _to_response(sample)

    def delete_enrollment(self, person_id: str, enrollment_id: str) -> None:
        sample = self._get_sample(person_id, enrollment_id)
        self._session.delete(sample)
        person = self._session.get(Person, person_id)
        if person is not None:
            person.updated_at = _utc_now()
        self._session.commit()
        logger.info(
            "Enrollment deleted person_id=%s enrollment_id=%s",
            person_id,
            enrollment_id,
        )

    def load_embedding_vector(self, person_id: str, enrollment_id: str) -> list[float]:
        """Internal/test helper. Not used by public GET APIs."""
        sample = self._get_sample(person_id, enrollment_id)
        return [float(value) for value in deserialize_embedding(sample.embedding)]

    def _require_person(self, person_id: str) -> Person:
        person = self._session.get(Person, person_id)
        if person is None:
            raise PersonNotFoundError(person_id)
        return person

    def _get_sample(self, person_id: str, enrollment_id: str) -> EnrollmentSample:
        self._require_person(person_id)
        sample = self._session.get(EnrollmentSample, enrollment_id)
        if sample is None or sample.person_id != person_id:
            raise EnrollmentNotFoundError(enrollment_id)
        return sample
