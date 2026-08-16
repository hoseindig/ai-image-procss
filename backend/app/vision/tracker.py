"""FaceTracker protocol. Application code depends on this, not a specific algorithm."""

from __future__ import annotations

from typing import Protocol

from app.vision.types import FaceDetection, FaceTrack


class FaceTracker(Protocol):
    def update(self, detections: list[FaceDetection]) -> list[FaceTrack]:
        """Associate detections with existing tracks and return the current set."""
        ...
