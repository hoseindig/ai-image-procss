"""Face quality assessment. Independent of YuNet and of future embedding models.

Metrics are engineering heuristics for gating alignment / future recognition.
They are not scientifically validated biometric quality scores.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from app.cameras.types import Frame
from app.core.logging import get_logger
from app.vision.types import (
    BoundingBox,
    FaceLandmarks,
    FaceQuality,
    FaceTrack,
    Point,
    QualityRejectionReason,
)

logger = get_logger("app.vision")

# Allow landmarks slightly outside the box / frame (detector jitter).
_LANDMARK_FRAME_MARGIN_PX = 8.0
_MIN_EYE_DISTANCE_PX = 4.0
_MIN_MOUTH_DISTANCE_PX = 2.0


@dataclass(frozen=True)
class QualityConfig:
    min_face_width: float
    min_face_height: float
    min_sharpness: float
    min_brightness: float
    max_brightness: float


class FaceQualityAssessor(Protocol):
    def assess(self, frame: Frame, face: FaceTrack) -> FaceQuality:
        """Evaluate whether a tracked face is suitable for alignment / future embedding."""
        ...


class HeuristicFaceQualityAssessor:
    """CPU-friendly size / blur / brightness / landmark / crop checks."""

    def __init__(self, config: QualityConfig) -> None:
        self._config = config
        logger.info(
            "Face quality assessor ready min_size=%sx%s min_sharpness=%.1f brightness=[%.1f, %.1f]",
            config.min_face_width,
            config.min_face_height,
            config.min_sharpness,
            config.min_brightness,
            config.max_brightness,
        )

    def assess(self, frame: Frame, face: FaceTrack) -> FaceQuality:
        box = face.bounding_box
        reasons: list[QualityRejectionReason] = []
        face_width = float(box.width)
        face_height = float(box.height)

        crop_ok, crop = _extract_face_crop(frame.data, box, frame.width, frame.height)
        if not crop_ok:
            reasons.append(QualityRejectionReason.INVALID_CROP)

        if face_width < self._config.min_face_width or face_height < self._config.min_face_height:
            reasons.append(QualityRejectionReason.FACE_TOO_SMALL)

        landmarks_valid = _landmarks_valid(
            face.landmarks,
            box,
            frame_width=frame.width,
            frame_height=frame.height,
        )
        if not landmarks_valid:
            reasons.append(QualityRejectionReason.INVALID_LANDMARKS)

        sharpness: float | None = None
        brightness: float | None = None
        if crop is not None:
            gray = _to_gray(crop)
            sharpness = _laplacian_variance(gray)
            brightness = float(np.mean(gray))
            if sharpness < self._config.min_sharpness:
                reasons.append(QualityRejectionReason.TOO_BLURRY)
            if brightness < self._config.min_brightness:
                reasons.append(QualityRejectionReason.TOO_DARK)
            elif brightness > self._config.max_brightness:
                reasons.append(QualityRejectionReason.TOO_BRIGHT)

        # Stable reason order for deterministic API / tests.
        ordered = _ordered_unique(reasons)
        return FaceQuality(
            track_id=face.track_id,
            accepted=len(ordered) == 0,
            reasons=ordered,
            face_width=face_width,
            face_height=face_height,
            sharpness=sharpness,
            brightness=brightness,
            landmarks_valid=landmarks_valid,
        )


def _ordered_unique(reasons: list[QualityRejectionReason]) -> list[QualityRejectionReason]:
    seen: set[QualityRejectionReason] = set()
    result: list[QualityRejectionReason] = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            result.append(reason)
    return result


def _extract_face_crop(
    image: NDArray[np.uint8],
    box: BoundingBox,
    frame_width: int,
    frame_height: int,
) -> tuple[bool, NDArray[np.uint8] | None]:
    if box.width <= 0 or box.height <= 0:
        return False, None
    x1 = int(math.floor(box.x))
    y1 = int(math.floor(box.y))
    x2 = int(math.ceil(box.x + box.width))
    y2 = int(math.ceil(box.y + box.height))
    if x2 <= x1 or y2 <= y1:
        return False, None
    if x2 <= 0 or y2 <= 0 or x1 >= frame_width or y1 >= frame_height:
        return False, None
    x1c = max(x1, 0)
    y1c = max(y1, 0)
    x2c = min(x2, frame_width)
    y2c = min(y2, frame_height)
    if x2c <= x1c or y2c <= y1c:
        return False, None
    crop = image[y1c:y2c, x1c:x2c]
    if crop.size == 0:
        return False, None
    return True, crop


def _to_gray(bgr: NDArray[np.uint8]) -> NDArray[np.uint8]:
    import cv2

    if bgr.ndim == 2:
        return bgr
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return np.asarray(gray, dtype=np.uint8)


def _laplacian_variance(gray: NDArray[np.uint8]) -> float:
    import cv2

    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(lap.var())


def _landmarks_valid(
    landmarks: FaceLandmarks,
    box: BoundingBox,
    *,
    frame_width: int,
    frame_height: int,
) -> bool:
    points = (
        landmarks.left_eye,
        landmarks.right_eye,
        landmarks.nose,
        landmarks.left_mouth,
        landmarks.right_mouth,
    )
    for point in points:
        if not _point_finite(point):
            return False
        if not _point_near_frame(
            point,
            frame_width=frame_width,
            frame_height=frame_height,
            margin=_LANDMARK_FRAME_MARGIN_PX,
        ):
            return False

    eye_dist = _distance(landmarks.left_eye, landmarks.right_eye)
    if eye_dist < _MIN_EYE_DISTANCE_PX:
        return False
    mouth_dist = _distance(landmarks.left_mouth, landmarks.right_mouth)
    if mouth_dist < _MIN_MOUTH_DISTANCE_PX:
        return False

    # Nose should sit roughly between the eyes horizontally and below them.
    eye_min_x = min(landmarks.left_eye.x, landmarks.right_eye.x)
    eye_max_x = max(landmarks.left_eye.x, landmarks.right_eye.x)
    eye_y = (landmarks.left_eye.y + landmarks.right_eye.y) / 2.0
    mouth_y = (landmarks.left_mouth.y + landmarks.right_mouth.y) / 2.0
    if not (eye_min_x - 1.0 <= landmarks.nose.x <= eye_max_x + 1.0):
        return False
    if landmarks.nose.y < eye_y:
        return False
    if mouth_y < landmarks.nose.y:
        return False

    # Landmarks should not be far outside the detection box.
    pad_x = max(box.width * 0.35, 8.0)
    pad_y = max(box.height * 0.35, 8.0)
    for point in points:
        if point.x < box.x - pad_x or point.x > box.x + box.width + pad_x:
            return False
        if point.y < box.y - pad_y or point.y > box.y + box.height + pad_y:
            return False
    return True


def _point_finite(point: Point) -> bool:
    return math.isfinite(point.x) and math.isfinite(point.y)


def _point_near_frame(
    point: Point,
    *,
    frame_width: int,
    frame_height: int,
    margin: float,
) -> bool:
    return (
        -margin <= point.x <= frame_width + margin and -margin <= point.y <= frame_height + margin
    )


def _distance(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)
