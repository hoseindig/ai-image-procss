"""Camera HTTP error mapping."""

from __future__ import annotations

from app.cameras.exceptions import (
    CameraAlreadyRunningError,
    CameraError,
    CameraInvalidStateError,
    CameraNotAvailableError,
    CameraNotFoundError,
    CameraOpenError,
    CameraReadError,
)


def camera_error_http_status(exc: CameraError) -> int:
    if isinstance(exc, CameraNotFoundError):
        return 404
    if isinstance(exc, CameraAlreadyRunningError | CameraInvalidStateError):
        return 409
    if isinstance(exc, CameraNotAvailableError | CameraOpenError | CameraReadError):
        return 503
    return 400
