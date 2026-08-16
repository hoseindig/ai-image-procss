"""Helpers for synthetic YuNet tensors. No model file required."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
from numpy.typing import NDArray

from app.cameras.types import Frame
from app.vision.decode import YUNET_STRIDES
from app.vision.geometry import padded_size
from app.vision.types import BoundingBox, FaceDetection, FaceLandmarks, Point


def empty_yunet_outputs(width: int, height: int) -> dict[str, NDArray[np.float32]]:
    pad_width, pad_height = padded_size(width, height)
    outputs: dict[str, NDArray[np.float32]] = {}
    for stride in YUNET_STRIDES:
        anchors = (pad_width // stride) * (pad_height // stride)
        outputs[f"cls_{stride}"] = np.zeros((1, anchors, 1), dtype=np.float32)
        outputs[f"obj_{stride}"] = np.zeros((1, anchors, 1), dtype=np.float32)
        outputs[f"bbox_{stride}"] = np.zeros((1, anchors, 4), dtype=np.float32)
        outputs[f"kps_{stride}"] = np.zeros((1, anchors, 10), dtype=np.float32)
    return outputs


def yunet_outputs_with_faces(
    width: int,
    height: int,
    faces: list[tuple[int, int, int]],
) -> dict[str, NDArray[np.float32]]:
    """Place synthetic faces at (stride, row, col) grid cells.

    Each face uses bbox offsets of 0, so the decoded box is `stride x stride`
    centered on the grid cell.
    """
    outputs = empty_yunet_outputs(width, height)
    pad_width, _pad_height = padded_size(width, height)
    for stride, row, col in faces:
        cols = pad_width // stride
        index = row * cols + col
        outputs[f"cls_{stride}"][0, index, 0] = 1.0
        outputs[f"obj_{stride}"][0, index, 0] = 1.0
    return outputs


def set_anchor_score(
    outputs: dict[str, NDArray[np.float32]],
    *,
    stride: int,
    row: int,
    col: int,
    width: int,
    height: int,
    cls: float,
    obj: float,
) -> None:
    pad_width, _pad_height = padded_size(width, height)
    index = row * (pad_width // stride) + col
    outputs[f"cls_{stride}"][0, index, 0] = cls
    outputs[f"obj_{stride}"][0, index, 0] = obj


def blank_frame(width: int, height: int, fill: int = 127) -> Frame:
    data = np.full((height, width, 3), fill, dtype=np.uint8)
    return Frame(data=data, timestamp=datetime.now(UTC), width=width, height=height)


def sample_face(
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    confidence: float = 0.92,
) -> FaceDetection:
    return FaceDetection(
        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
        confidence=confidence,
        landmarks=FaceLandmarks(
            left_eye=Point(x=x + width * 0.3, y=y + height * 0.35),
            right_eye=Point(x=x + width * 0.7, y=y + height * 0.35),
            nose=Point(x=x + width * 0.5, y=y + height * 0.55),
            left_mouth=Point(x=x + width * 0.35, y=y + height * 0.75),
            right_mouth=Point(x=x + width * 0.65, y=y + height * 0.75),
        ),
    )
