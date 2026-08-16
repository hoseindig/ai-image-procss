"""Draw face detections onto a BGR image. Kept separate from FaceDetector."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from app.vision.types import FaceDetection


def draw_detections(
    image: NDArray[np.uint8],
    faces: list[FaceDetection],
) -> NDArray[np.uint8]:
    """Return a copy of `image` with boxes, landmarks, and detection confidence."""
    import cv2

    output = np.ascontiguousarray(image.copy())
    for face in faces:
        box = face.bounding_box
        x1 = int(round(box.x))
        y1 = int(round(box.y))
        x2 = int(round(box.x + box.width))
        y2 = int(round(box.y + box.height))
        cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"Face {face.confidence:.2f}"
        text_y = y1 - 8 if y1 > 16 else y1 + 16
        cv2.putText(
            output,
            label,
            (x1, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )
        landmarks = face.landmarks
        points = (
            (landmarks.right_eye, (255, 0, 0)),
            (landmarks.left_eye, (0, 0, 255)),
            (landmarks.nose, (0, 255, 0)),
            (landmarks.right_mouth, (255, 0, 255)),
            (landmarks.left_mouth, (0, 255, 255)),
        )
        for point, color in points:
            cv2.circle(output, (int(round(point.x)), int(round(point.y))), 2, color, -1)
    return output
