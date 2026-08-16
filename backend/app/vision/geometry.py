"""Resize/pad helpers and mapping from model input coordinates to the original frame.

Detection coordinates are always expressed in the original frame:

- origin: top-left
- units: pixels
- x increases right, y increases down

YuNet sees a resized (and possibly padded) image. Mapping undoes that transform.
Padding is applied on the bottom and right only, so content at (0, 0) stays at (0, 0).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from app.vision.types import BoundingBox, FaceDetection, FaceLandmarks, Point

YUNET_STRIDE_DIVISOR = 32


@dataclass(frozen=True)
class CoordinateMapper:
    """Maps points from the resized model-input image back to the original frame."""

    original_width: int
    original_height: int
    input_width: int
    input_height: int

    def to_original_x(self, value: float) -> float:
        return value * (self.original_width / self.input_width)

    def to_original_y(self, value: float) -> float:
        return value * (self.original_height / self.input_height)

    def point(self, x: float, y: float) -> Point:
        return Point(x=self.to_original_x(x), y=self.to_original_y(y))

    def box(self, x: float, y: float, width: float, height: float) -> BoundingBox:
        return BoundingBox(
            x=self.to_original_x(x),
            y=self.to_original_y(y),
            width=self.to_original_x(width),
            height=self.to_original_y(height),
        )


def padded_size(width: int, height: int, divisor: int = YUNET_STRIDE_DIVISOR) -> tuple[int, int]:
    pad_w = ((width - 1) // divisor + 1) * divisor
    pad_h = ((height - 1) // divisor + 1) * divisor
    return pad_w, pad_h


def resize_bgr(image: NDArray[np.uint8], width: int, height: int) -> NDArray[np.uint8]:
    """Resize a BGR image to (width, height). OpenCV is confined to this helper."""
    import cv2

    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Expected an HxWx3 BGR image")
    if image.shape[1] == width and image.shape[0] == height:
        return np.ascontiguousarray(image)
    resized = np.asarray(
        cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR),
        dtype=np.uint8,
    )
    return np.ascontiguousarray(resized)


def pad_bottom_right(
    image: NDArray[np.uint8], pad_width: int, pad_height: int
) -> NDArray[np.uint8]:
    height, width = image.shape[0], image.shape[1]
    if width == pad_width and height == pad_height:
        return np.ascontiguousarray(image)
    if pad_width < width or pad_height < height:
        raise ValueError("Padded size must be greater than or equal to the image size")
    padded = np.zeros((pad_height, pad_width, image.shape[2]), dtype=image.dtype)
    padded[:height, :width] = image
    return padded


def bgr_to_nchw_float(image: NDArray[np.uint8]) -> NDArray[np.float32]:
    """Convert HxWx3 uint8 BGR to 1x3xHxW float32 with no mean/std normalization."""
    blob = np.ascontiguousarray(image.transpose(2, 0, 1)[np.newaxis], dtype=np.float32)
    return blob


def clip_detection(detection: FaceDetection, width: int, height: int) -> FaceDetection:
    box = detection.bounding_box
    x1 = min(max(box.x, 0.0), float(width))
    y1 = min(max(box.y, 0.0), float(height))
    x2 = min(max(box.x + box.width, 0.0), float(width))
    y2 = min(max(box.y + box.height, 0.0), float(height))
    return detection.model_copy(
        update={
            "bounding_box": BoundingBox(
                x=x1,
                y=y1,
                width=max(x2 - x1, 0.0),
                height=max(y2 - y1, 0.0),
            ),
            "landmarks": FaceLandmarks(
                left_eye=_clip_point(detection.landmarks.left_eye, width, height),
                right_eye=_clip_point(detection.landmarks.right_eye, width, height),
                nose=_clip_point(detection.landmarks.nose, width, height),
                left_mouth=_clip_point(detection.landmarks.left_mouth, width, height),
                right_mouth=_clip_point(detection.landmarks.right_mouth, width, height),
            ),
        }
    )


def _clip_point(point: Point, width: int, height: int) -> Point:
    return Point(
        x=min(max(point.x, 0.0), float(width)),
        y=min(max(point.y, 0.0), float(height)),
    )
