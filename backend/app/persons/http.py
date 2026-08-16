"""Person/enrollment HTTP error mapping."""

from __future__ import annotations

from app.persons.exceptions import (
    EnrollmentNotFoundError,
    EnrollmentQualityRejectedError,
    InvalidEmbeddingError,
    PersonConflictError,
    PersonError,
    PersonInactiveError,
    PersonNotFoundError,
    PersonValidationError,
)


def person_error_http_status(exc: PersonError) -> int:
    if isinstance(exc, PersonNotFoundError | EnrollmentNotFoundError):
        return 404
    if isinstance(exc, PersonConflictError):
        return 409
    if isinstance(
        exc,
        PersonValidationError
        | InvalidEmbeddingError
        | EnrollmentQualityRejectedError
        | PersonInactiveError,
    ):
        return 400
    return 400
