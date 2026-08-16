"""CameraSource protocol. Application code depends on this, not OpenCV."""

from __future__ import annotations

from typing import Protocol

from app.cameras.types import CameraStatus, Frame


class CameraSource(Protocol):
    def open(self) -> None:
        """Acquire the device. Must succeed before start()."""

    def start(self) -> None:
        """Begin capturing into the latest-frame slot."""

    def read(self) -> Frame | None:
        """Return the most recent frame, or None if none is available yet."""

    def stop(self) -> None:
        """Stop capturing. The device may remain open."""

    def close(self) -> None:
        """Release the device. Idempotent. Stops capture if still running."""

    def is_open(self) -> bool:
        """True when the device handle is held (open, running, or stopped)."""

    def is_running(self) -> bool:
        """True when the capture loop is active."""

    def get_status(self) -> CameraStatus:
        """Current status snapshot."""
