"""Construct the process FaceDetector from settings. No runtime model download."""

from __future__ import annotations

from pathlib import Path

from app.core.config import PROJECT_ROOT, Settings
from app.core.logging import get_logger
from app.vision.engine import OnnxRuntimeEngine
from app.vision.exceptions import ModelNotFoundError
from app.vision.iou_tracker import IoUCentroidFaceTracker, TrackerConfig
from app.vision.tracker import FaceTracker
from app.vision.yunet import YuNetConfig, YuNetFaceDetector

logger = get_logger("app.vision")


def resolve_model_path(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def create_face_detector(settings: Settings) -> YuNetFaceDetector:
    model_path = resolve_model_path(settings.face_detection_model_path)
    if not model_path.is_file():
        raise ModelNotFoundError(str(model_path))
    logger.info("Loading YuNet model path=%s", model_path)
    engine = OnnxRuntimeEngine(model_path)
    config = YuNetConfig(
        confidence_threshold=settings.face_detection_confidence_threshold,
        nms_threshold=settings.face_detection_nms_threshold,
        input_width=settings.face_detection_input_width,
        input_height=settings.face_detection_input_height,
        max_faces=settings.face_detection_max_faces,
    )
    return YuNetFaceDetector(engine, config)


def create_face_tracker(settings: Settings) -> FaceTracker | None:
    if not settings.face_tracking_enabled:
        return None
    config = TrackerConfig(
        iou_threshold=settings.face_tracking_iou_threshold,
        max_centroid_distance=settings.face_tracking_max_centroid_distance,
        max_missed_frames=settings.face_tracking_max_missed_frames,
        min_confirmed_frames=settings.face_tracking_min_confirmed_frames,
        max_tracks=settings.face_tracking_max_tracks,
    )
    return IoUCentroidFaceTracker(config)
