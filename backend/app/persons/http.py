"""Person/enrollment HTTP error mapping."""

from __future__ import annotations

from app.persons.exceptions import (
    EnrollmentCaptureNotReadyError,
    EnrollmentNotFoundError,
    EnrollmentQualityRejectedError,
    EnrollmentSessionConflictError,
    EnrollmentSessionNotFoundError,
    InvalidEmbeddingError,
    PersonConflictError,
    PersonError,
    PersonInactiveError,
    PersonNotFoundError,
    PersonValidationError,
)


def person_error_http_status(exc: PersonError) -> int:
    if isinstance(
        exc,
        PersonNotFoundError | EnrollmentNotFoundError | EnrollmentSessionNotFoundError,
    ):
        return 404
    if isinstance(exc, PersonConflictError | EnrollmentSessionConflictError):
        return 409
    if isinstance(
        exc,
        PersonValidationError
        | InvalidEmbeddingError
        | EnrollmentQualityRejectedError
        | PersonInactiveError
        | EnrollmentCaptureNotReadyError,
    ):
        return 400
    return 400
