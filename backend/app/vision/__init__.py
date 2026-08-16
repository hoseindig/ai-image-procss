"""Vision package. Application code depends on protocols, not YuNet."""

from app.vision.align import AlignedFace, FaceAligner
from app.vision.detector import FaceDetector
from app.vision.exceptions import (
    InferenceError,
    InferenceProviderError,
    ModelLoadError,
    ModelNotFoundError,
    VisionError,
)
from app.vision.quality import FaceQualityAssessor
from app.vision.runtime import DetectionRuntime
from app.vision.tracker import FaceTracker
from app.vision.types import (
    BoundingBox,
    DetectionSnapshot,
    FaceDetection,
    FaceLandmarks,
    FaceQuality,
    FaceTrack,
    Point,
    QualityRejectionReason,
    TrackState,
)

__all__ = [
    "AlignedFace",
    "BoundingBox",
    "DetectionRuntime",
    "DetectionSnapshot",
    "FaceAligner",
    "FaceDetection",
    "FaceDetector",
    "FaceLandmarks",
    "FaceQuality",
    "FaceQualityAssessor",
    "FaceTrack",
    "FaceTracker",
    "InferenceError",
    "InferenceProviderError",
    "ModelLoadError",
    "ModelNotFoundError",
    "Point",
    "QualityRejectionReason",
    "TrackState",
    "VisionError",
]
