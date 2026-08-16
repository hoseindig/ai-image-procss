"""Vision package. Application code depends on FaceDetector, not YuNet."""

from app.vision.detector import FaceDetector
from app.vision.exceptions import (
    InferenceError,
    InferenceProviderError,
    ModelLoadError,
    ModelNotFoundError,
    VisionError,
)
from app.vision.runtime import DetectionRuntime
from app.vision.types import (
    BoundingBox,
    DetectionSnapshot,
    FaceDetection,
    FaceLandmarks,
    Point,
)

__all__ = [
    "BoundingBox",
    "DetectionRuntime",
    "DetectionSnapshot",
    "FaceDetection",
    "FaceDetector",
    "FaceLandmarks",
    "InferenceError",
    "InferenceProviderError",
    "ModelLoadError",
    "ModelNotFoundError",
    "Point",
    "VisionError",
]
