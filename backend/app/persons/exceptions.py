"""Domain errors for person enrollment. API handlers map these to HTTP."""


class PersonError(Exception):
    """Base person/enrollment error. Safe to convert to an API response."""

    def __init__(self, message: str, *, code: str = "person_error") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class PersonNotFoundError(PersonError):
    def __init__(self, person_id: str) -> None:
        super().__init__(f"Person '{person_id}' was not found", code="person_not_found")
        self.person_id = person_id


class PersonValidationError(PersonError):
    def __init__(self, message: str, *, code: str = "person_validation_error") -> None:
        super().__init__(message, code=code)


class PersonConflictError(PersonError):
    def __init__(self, message: str, *, code: str = "person_conflict") -> None:
        super().__init__(message, code=code)


class PersonInactiveError(PersonError):
    def __init__(self, person_id: str) -> None:
        super().__init__(
            f"Person '{person_id}' is inactive; enrollment is not allowed",
            code="person_inactive",
        )
        self.person_id = person_id


class EnrollmentNotFoundError(PersonError):
    def __init__(self, enrollment_id: str) -> None:
        super().__init__(
            f"Enrollment '{enrollment_id}' was not found",
            code="enrollment_not_found",
        )
        self.enrollment_id = enrollment_id


class InvalidEmbeddingError(PersonError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_embedding")


class EnrollmentQualityRejectedError(PersonError):
    def __init__(self, message: str = "Enrollment requires quality.accepted == true") -> None:
        super().__init__(message, code="enrollment_quality_rejected")


class EnrollmentSessionNotFoundError(PersonError):
    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"Enrollment session '{session_id}' was not found",
            code="enrollment_session_not_found",
        )
        self.session_id = session_id


class EnrollmentSessionConflictError(PersonError):
    def __init__(self, message: str, *, code: str = "enrollment_session_conflict") -> None:
        super().__init__(message, code=code)


class EnrollmentCaptureNotReadyError(PersonError):
    def __init__(self, message: str, *, code: str = "enrollment_not_ready") -> None:
        super().__init__(message, code=code)
