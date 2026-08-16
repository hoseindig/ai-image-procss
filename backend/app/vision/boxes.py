"""Bounding-box geometry for tracking. Operates in original-frame pixels."""

from __future__ import annotations

import math

from app.vision.types import BoundingBox


def box_iou(left: BoundingBox, right: BoundingBox) -> float:
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


def box_centroid(box: BoundingBox) -> tuple[float, float]:
    return (box.x + box.width / 2.0, box.y + box.height / 2.0)


def centroid_distance(left: BoundingBox, right: BoundingBox) -> float:
    left_c = box_centroid(left)
    right_c = box_centroid(right)
    return math.hypot(left_c[0] - right_c[0], left_c[1] - right_c[1])
