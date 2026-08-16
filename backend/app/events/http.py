"""Event HTTP error mapping."""

from __future__ import annotations

from app.events.exceptions import EventError, EventNotFoundError, EventValidationError


def event_error_http_status(exc: EventError) -> int:
    if isinstance(exc, EventNotFoundError):
        return 404
    if isinstance(exc, EventValidationError):
        return 400
    return 400
