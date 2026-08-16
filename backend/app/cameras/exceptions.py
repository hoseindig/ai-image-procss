"""Domain errors for the camera subsystem. API handlers map these to HTTP."""


class CameraError(Exception):
    """Base camera error. Safe to convert to an API response."""

    def __init__(self, message: str, *, code: str = "camera_error") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class CameraNotFoundError(CameraError):
    def __init__(self, camera_id: str) -> None:
        super().__init__(f"Camera '{camera_id}' was not found", code="camera_not_found")
        self.camera_id = camera_id


class CameraOpenError(CameraError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="camera_open_failed")


class CameraReadError(CameraError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="camera_read_failed")


class CameraNotAvailableError(CameraError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="camera_not_available")


class CameraAlreadyRunningError(CameraError):
    def __init__(self, camera_id: str) -> None:
        super().__init__(f"Camera '{camera_id}' is already running", code="camera_already_running")
        self.camera_id = camera_id


class CameraInvalidStateError(CameraError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="camera_invalid_state")
