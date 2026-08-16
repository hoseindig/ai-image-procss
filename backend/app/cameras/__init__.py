"""Camera subsystem. Higher-level code depends on CameraSource, not OpenCV."""

from app.cameras.exceptions import (
    CameraAlreadyRunningError,
    CameraError,
    CameraInvalidStateError,
    CameraNotAvailableError,
    CameraNotFoundError,
    CameraOpenError,
    CameraReadError,
)
from app.cameras.manager import CameraManager
from app.cameras.source import CameraSource
from app.cameras.types import CameraConfig, CameraState, CameraStatus, Frame, SourceType
from app.cameras.usb import UsbCameraSource

__all__ = [
    "CameraAlreadyRunningError",
    "CameraConfig",
    "CameraError",
    "CameraInvalidStateError",
    "CameraManager",
    "CameraNotAvailableError",
    "CameraNotFoundError",
    "CameraOpenError",
    "CameraReadError",
    "CameraSource",
    "CameraState",
    "CameraStatus",
    "Frame",
    "SourceType",
    "UsbCameraSource",
]
