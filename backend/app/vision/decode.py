"""YuNet head decode and NMS.

Post-processing follows OpenCV's FaceDetectorYN (MIT, opencv/modules/objdetect).
Coordinates are in the padded model-input image (top-left origin).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from app.vision.exceptions import InferenceError

YUNET_STRIDES = (8, 16, 32)
YUNET_OUTPUT_NAMES = (
    "cls_8",
    "cls_16",
    "cls_32",
    "obj_8",
    "obj_16",
    "obj_32",
    "bbox_8",
    "bbox_16",
    "bbox_32",
    "kps_8",
    "kps_16",
    "kps_32",
)


@dataclass(frozen=True)
class RawFace:
    """One decoded face in padded/resized model-input pixels."""

    x: float
    y: float
    width: float
    height: float
    confidence: float
    right_eye_x: float
    right_eye_y: float
    left_eye_x: float
    left_eye_y: float
    nose_x: float
    nose_y: float
    right_mouth_x: float
    right_mouth_y: float
    left_mouth_x: float
    left_mouth_y: float


def decode_yunet(
    outputs: dict[str, NDArray[np.float32]],
    *,
    pad_width: int,
    pad_height: int,
    score_threshold: float,
    nms_threshold: float,
    max_faces: int,
) -> list[RawFace]:
    """Decode YuNet heads into faces, then apply confidence filter and NMS."""
    missing = [name for name in YUNET_OUTPUT_NAMES if name not in outputs]
    if missing:
        raise InferenceError(f"YuNet output tensors missing: {', '.join(missing)}")

    candidates: list[RawFace] = []
    for stride in YUNET_STRIDES:
        candidates.extend(
            _decode_stride(
                cls=_as_heads(outputs[f"cls_{stride}"]),
                obj=_as_heads(outputs[f"obj_{stride}"]),
                bbox=_as_heads(outputs[f"bbox_{stride}"]),
                kps=_as_heads(outputs[f"kps_{stride}"]),
                stride=stride,
                pad_width=pad_width,
                pad_height=pad_height,
                score_threshold=score_threshold,
            )
        )
    if not candidates:
        return []
    if len(candidates) == 1:
        return candidates[:max_faces]
    kept = nms(candidates, iou_threshold=nms_threshold, max_faces=max_faces)
    return kept


def nms(faces: list[RawFace], *, iou_threshold: float, max_faces: int) -> list[RawFace]:
    """Greedy IoU NMS. Highest detection confidence first."""
    if not faces:
        return []
    order = sorted(range(len(faces)), key=lambda index: faces[index].confidence, reverse=True)
    kept: list[int] = []
    while order and len(kept) < max_faces:
        current = order[0]
        kept.append(current)
        rest = order[1:]
        order = [index for index in rest if _iou(faces[current], faces[index]) <= iou_threshold]
    return [faces[index] for index in kept]


def _decode_stride(
    *,
    cls: NDArray[np.float32],
    obj: NDArray[np.float32],
    bbox: NDArray[np.float32],
    kps: NDArray[np.float32],
    stride: int,
    pad_width: int,
    pad_height: int,
    score_threshold: float,
) -> list[RawFace]:
    cols = pad_width // stride
    rows = pad_height // stride
    expected = rows * cols
    cls_flat = cls.reshape(-1)
    obj_flat = obj.reshape(-1)
    if cls_flat.size < expected or obj_flat.size < expected:
        raise InferenceError(
            f"YuNet stride {stride} tensor is too small: expected {expected} anchors"
        )
    bbox_view = bbox.reshape(-1, 4)
    kps_view = kps.reshape(-1, 10)
    if bbox_view.shape[0] < expected or kps_view.shape[0] < expected:
        raise InferenceError(f"YuNet stride {stride} box/landmark tensor is too small")

    cls_score = np.clip(cls_flat[:expected], 0.0, 1.0)
    obj_score = np.clip(obj_flat[:expected], 0.0, 1.0)
    scores = np.sqrt(cls_score * obj_score)
    selected = np.nonzero(scores >= score_threshold)[0]
    if selected.size == 0:
        return []

    col = (selected % cols).astype(np.float32)
    row = (selected // cols).astype(np.float32)
    chosen_bbox = bbox_view[selected]
    chosen_kps = kps_view[selected]
    cx = (col + chosen_bbox[:, 0]) * stride
    cy = (row + chosen_bbox[:, 1]) * stride
    width = np.exp(chosen_bbox[:, 2]) * stride
    height = np.exp(chosen_bbox[:, 3]) * stride
    x = cx - width / 2.0
    y = cy - height / 2.0

    faces: list[RawFace] = []
    for index in range(selected.size):
        kps_row = chosen_kps[index]
        faces.append(
            RawFace(
                x=float(x[index]),
                y=float(y[index]),
                width=float(width[index]),
                height=float(height[index]),
                confidence=float(scores[selected[index]]),
                right_eye_x=float((col[index] + kps_row[0]) * stride),
                right_eye_y=float((row[index] + kps_row[1]) * stride),
                left_eye_x=float((col[index] + kps_row[2]) * stride),
                left_eye_y=float((row[index] + kps_row[3]) * stride),
                nose_x=float((col[index] + kps_row[4]) * stride),
                nose_y=float((row[index] + kps_row[5]) * stride),
                right_mouth_x=float((col[index] + kps_row[6]) * stride),
                right_mouth_y=float((row[index] + kps_row[7]) * stride),
                left_mouth_x=float((col[index] + kps_row[8]) * stride),
                left_mouth_y=float((row[index] + kps_row[9]) * stride),
            )
        )
    return faces


def _as_heads(value: NDArray[np.float32]) -> NDArray[np.float32]:
    array = np.asarray(value, dtype=np.float32)
    if array.ndim == 3 and array.shape[0] == 1:
        return np.asarray(array[0], dtype=np.float32)
    return array


def _iou(left: RawFace, right: RawFace) -> float:
    left_x2 = left.x + left.width
    left_y2 = left.y + left.height
    right_x2 = right.x + right.width
    right_y2 = right.y + right.height
    overlap_w = max(0.0, min(left_x2, right_x2) - max(left.x, right.x))
    overlap_h = max(0.0, min(left_y2, right_y2) - max(left.y, right.y))
    overlap = overlap_w * overlap_h
    union = left.width * left.height + right.width * right.height - overlap
    if union <= 0:
        return 0.0
    return overlap / union
