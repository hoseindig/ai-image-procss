"""Person CRUD. Does not touch SFace or recognition."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.person import EnrollmentSample, Person
from app.persons.exceptions import (
    PersonConflictError,
    PersonNotFoundError,
    PersonValidationError,
)
from app.schemas.person import DISPLAY_NAME_MAX_LENGTH, PersonResponse

logger = get_logger("app.persons")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_display_name(display_name: str) -> str:
    trimmed = display_name.strip()
    if not trimmed:
        raise PersonValidationError("display_name must be non-empty after trimming")
    if len(trimmed) > DISPLAY_NAME_MAX_LENGTH:
        raise PersonValidationError(
            f"display_name must be at most {DISPLAY_NAME_MAX_LENGTH} characters"
        )
    return trimmed


def _to_response(person: Person, enrollment_count: int) -> PersonResponse:
    return PersonResponse(
        id=person.id,
        display_name=person.display_name,
        active=person.active,
        created_at=person.created_at,
        updated_at=person.updated_at,
        enrollment_count=enrollment_count,
    )


class PersonService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_person(self, display_name: str) -> PersonResponse:
        name = normalize_display_name(display_name)
        now = _utc_now()
        person = Person(
            id=str(uuid4()),
            display_name=name,
            active=True,
            created_at=now,
            updated_at=now,
        )
        self._session.add(person)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise PersonConflictError(
                f"A person with display_name '{name}' already exists"
            ) from exc
        self._session.refresh(person)
        logger.info("Person created person_id=%s", person.id)
        return _to_response(person, 0)

    def list_persons(self, *, include_inactive: bool = True) -> list[PersonResponse]:
        count_rows = self._session.execute(
            select(EnrollmentSample.person_id, func.count()).group_by(EnrollmentSample.person_id)
        ).all()
        counts: dict[str, int] = {str(person_id): int(count) for person_id, count in count_rows}
        query = select(Person).order_by(Person.created_at.asc())
        if not include_inactive:
            query = query.where(Person.active.is_(True))
        persons = list(self._session.scalars(query).all())
        return [_to_response(person, counts.get(person.id, 0)) for person in persons]

    def get_person(self, person_id: str) -> PersonResponse:
        person = self._get_person_row(person_id)
        count = self._enrollment_count(person_id)
        return _to_response(person, count)

    def update_person(
        self,
        person_id: str,
        *,
        display_name: str | None = None,
        active: bool | None = None,
    ) -> PersonResponse:
        person = self._get_person_row(person_id)
        if display_name is None and active is None:
            raise PersonValidationError("At least one of display_name or active must be provided")
        if display_name is not None:
            person.display_name = normalize_display_name(display_name)
        if active is not None:
            person.active = active
        person.updated_at = _utc_now()
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise PersonConflictError(
                f"A person with display_name '{person.display_name}' already exists"
            ) from exc
        self._session.refresh(person)
        logger.info(
            "Person updated person_id=%s active=%s",
            person.id,
            person.active,
        )
        return _to_response(person, self._enrollment_count(person_id))

    def deactivate_person(self, person_id: str) -> PersonResponse:
        return self.update_person(person_id, active=False)

    def activate_person(self, person_id: str) -> PersonResponse:
        return self.update_person(person_id, active=True)

    def _get_person_row(self, person_id: str) -> Person:
        person = self._session.get(Person, person_id)
        if person is None:
            raise PersonNotFoundError(person_id)
        return person

    def _enrollment_count(self, person_id: str) -> int:
        value = self._session.scalar(
            select(func.count())
            .select_from(EnrollmentSample)
            .where(EnrollmentSample.person_id == person_id)
        )
        return int(value or 0)
