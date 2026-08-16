"""Domain errors for the event subsystem."""


class EventError(Exception):
    def __init__(self, message: str, *, code: str = "event_error") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class EventNotFoundError(EventError):
    def __init__(self, event_id: str) -> None:
        super().__init__(f"Event '{event_id}' was not found", code="event_not_found")
        self.event_id = event_id


class EventValidationError(EventError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="event_validation_error")
