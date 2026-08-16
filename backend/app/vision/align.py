"""Five-point landmark face alignment. Independent of YuNet and SFace inference.

Produces a deterministic aligned crop suitable for a future embedder (e.g. SFace
expects 112×112). Output size is configurable; ArcFace reference points scale
with width/height.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from app.cameras.types import Frame
from app.core.logging import get_logger
from app.vision.types import FaceLandmarks, FaceTrack, Point

logger = get_logger("app.vision")

# ArcFace / InsightFace 112×112 template (image-left eye first).
# Source landmark order used with this template:
#   left_eye, right_eye, nose, left_mouth, right_mouth
# (FaceLandmarks field names; sample helpers place left_* at smaller x.)
_ARCFACE_112_TARGETS: tuple[tuple[float, float], ...] = (
    (38.2946, 51.6963),
    (73.5318, 51.5014),
    (56.0252, 71.7366),
    (41.5493, 92.3655),
    (70.7299, 92.2041),
)

# Geometry tests compare transformed landmarks to targets within this tolerance (px).
ALIGNMENT_LANDMARK_TOLERANCE_PX = 2.0


@dataclass(frozen=True)
class AlignConfig:
    output_width: int
    output_height: int


@dataclass(frozen=True)
class AlignedFace:
    """Aligned face crop. `image` is HxWx3 uint8 BGR. Track ID is not a person ID."""

    image: NDArray[np.uint8]
    width: int
    height: int
    source_track_id: int
    transform: NDArray[np.float64]


class FaceAligner(Protocol):
    def align(self, frame: Frame, face: FaceTrack) -> AlignedFace:
        """Warp the face region to a standardized crop using five landmarks."""
        ...


class LandmarkFaceAligner:
    """Similarity transform via OpenCV estimateAffinePartial2D + warpAffine."""

    def __init__(self, config: AlignConfig) -> None:
        self._config = config
        self._targets = _scaled_targets(config.output_width, config.output_height)
        logger.info(
            "Face aligner ready output=%sx%s interpolation=bilinear border=constant",
            config.output_width,
            config.output_height,
        )

    @property
    def targets(self) -> NDArray[np.float64]:
        return self._targets.copy()

    def align(self, frame: Frame, face: FaceTrack) -> AlignedFace:
        import cv2

        source = _landmark_matrix(face.landmarks)
        transform, inliers = cv2.estimateAffinePartial2D(
            source,
            self._targets,
            method=cv2.LMEDS,
        )
        if transform is None or inliers is None or int(np.count_nonzero(inliers)) < 3:
            # Deterministic fallback: use cv2.getAffineTransform on eyes+nose.
            transform = _affine_from_three(source, self._targets)

        aligned = cv2.warpAffine(
            frame.data,
            transform,
            (self._config.output_width, self._config.output_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )
        image = np.asarray(aligned, dtype=np.uint8)
        return AlignedFace(
            image=image,
            width=self._config.output_width,
            height=self._config.output_height,
            source_track_id=face.track_id,
            transform=np.asarray(transform, dtype=np.float64),
        )


def landmark_targets(width: int, height: int) -> NDArray[np.float64]:
    """Public helper for tests: expected aligned landmark positions."""
    return _scaled_targets(width, height)


def apply_affine_to_points(
    points: NDArray[np.float64],
    transform: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Apply a 2×3 affine matrix to Nx2 points. Used by geometry tests."""
    ones = np.ones((points.shape[0], 1), dtype=np.float64)
    homo = np.hstack([points, ones])
    return homo @ transform.T


def _scaled_targets(width: int, height: int) -> NDArray[np.float64]:
    scale_x = width / 112.0
    scale_y = height / 112.0
    return np.array(
        [[x * scale_x, y * scale_y] for x, y in _ARCFACE_112_TARGETS],
        dtype=np.float64,
    )


def _landmark_matrix(landmarks: FaceLandmarks) -> NDArray[np.float64]:
    return np.array(
        [
            _xy(landmarks.left_eye),
            _xy(landmarks.right_eye),
            _xy(landmarks.nose),
            _xy(landmarks.left_mouth),
            _xy(landmarks.right_mouth),
        ],
        dtype=np.float64,
    )


def _xy(point: Point) -> list[float]:
    return [float(point.x), float(point.y)]


def _affine_from_three(
    source: NDArray[np.float64],
    targets: NDArray[np.float64],
) -> NDArray[np.float64]:
    import cv2

    # Eyes + nose are the most stable triangle for a similarity fallback.
    return cv2.getAffineTransform(
        source[:3].astype(np.float32),
        targets[:3].astype(np.float32),
    ).astype(np.float64)
