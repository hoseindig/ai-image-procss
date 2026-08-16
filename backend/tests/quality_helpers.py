"""Helpers for face quality / alignment tests. No webcam or network."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
from numpy.typing import NDArray

from app.cameras.types import Frame
from app.vision.types import (
    BoundingBox,
    FaceLandmarks,
    FaceTrack,
    Point,
    TrackState,
)
from tests.yunet_helpers import sample_face


def track_from_box(
    *,
    track_id: int = 1,
    x: float,
    y: float,
    width: float,
    height: float,
    confidence: float = 0.92,
    state: TrackState = TrackState.CONFIRMED,
    landmarks: FaceLandmarks | None = None,
) -> FaceTrack:
    face = sample_face(x=x, y=y, width=width, height=height, confidence=confidence)
    return FaceTrack(
        track_id=track_id,
        bounding_box=face.bounding_box
        if landmarks is None
        else BoundingBox(x=x, y=y, width=width, height=height),
        confidence=confidence,
        landmarks=landmarks if landmarks is not None else face.landmarks,
        age_frames=3,
        missed_frames=0,
        state=state,
    )


def textured_frame(
    width: int,
    height: int,
    *,
    face_box: tuple[int, int, int, int] | None = None,
    face_fill: int | None = None,
    blur_face: bool = False,
) -> Frame:
    """Build a BGR frame with optional checkerboard face region (high sharpness)."""
    data = np.full((height, width, 3), 30, dtype=np.uint8)
    if face_box is not None:
        x, y, w, h = face_box
        region = _checkerboard(w, h, base=face_fill if face_fill is not None else 110)
        if blur_face:
            import cv2

            region = np.asarray(cv2.GaussianBlur(region, (31, 31), 0), dtype=np.uint8)
        data[y : y + h, x : x + w] = region
    return Frame(data=data, timestamp=datetime.now(UTC), width=width, height=height)


def solid_face_frame(
    width: int,
    height: int,
    *,
    face_box: tuple[int, int, int, int],
    value: int,
) -> Frame:
    data = np.full((height, width, 3), 80, dtype=np.uint8)
    x, y, w, h = face_box
    data[y : y + h, x : x + w] = value
    return Frame(data=data, timestamp=datetime.now(UTC), width=width, height=height)


def _checkerboard(width: int, height: int, *, base: int = 110) -> NDArray[np.uint8]:
    yy, xx = np.indices((height, width))
    mask = ((xx // 4) + (yy // 4)) % 2 == 0
    region = np.empty((height, width, 3), dtype=np.uint8)
    low = max(base - 50, 0)
    high = min(base + 50, 255)
    region[mask] = (low, low, low)
    region[~mask] = (high, high, high)
    return region


def collapsed_landmarks(*, x: float, y: float, width: float, height: float) -> FaceLandmarks:
    center = Point(x=x + width / 2.0, y=y + height / 2.0)
    return FaceLandmarks(
        left_eye=center,
        right_eye=center,
        nose=center,
        left_mouth=center,
        right_mouth=center,
    )
