"""FaceDetector protocol. Application code depends on this, not YuNet or ONNX Runtime."""

from __future__ import annotations

from typing import Protocol

from app.cameras.types import Frame
from app.vision.types import FaceDetection


class FaceDetector(Protocol):
    def detect(self, frame: Frame) -> list[FaceDetection]:
        """Return faces in original-frame coordinates."""
        ...
