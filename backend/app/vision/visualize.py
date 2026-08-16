"""Draw face detections and tracks onto a BGR image.

Kept separate from FaceDetector and FaceTracker. This module only renders.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from app.vision.types import BoundingBox, FaceDetection, FaceLandmarks, FaceTrack, TrackState


def draw_detections(
    image: NDArray[np.uint8],
    faces: list[FaceDetection],
) -> NDArray[np.uint8]:
    """Return a copy of `image` with boxes, landmarks, and detection confidence."""
    output = np.ascontiguousarray(image.copy())
    for face in faces:
        _draw_box(
            output,
            face.bounding_box,
            face.landmarks,
            f"Face {face.confidence:.2f}",
            (0, 255, 0),
        )
    return output


def draw_tracks(
    image: NDArray[np.uint8],
    tracks: list[FaceTrack],
) -> NDArray[np.uint8]:
    """Return a copy of `image` with track IDs, boxes, and landmarks."""
    output = np.ascontiguousarray(image.copy())
    for track in tracks:
        color = _track_color(track.state)
        label = f"Track #{track.track_id} {track.confidence:.2f}"
        _draw_box(output, track.bounding_box, track.landmarks, label, color)
    return output


def _track_color(state: TrackState) -> tuple[int, int, int]:
    if state is TrackState.CONFIRMED:
        return (0, 255, 0)
    if state is TrackState.TENTATIVE:
        return (0, 255, 255)
    return (128, 128, 128)


def _draw_box(
    output: NDArray[np.uint8],
    box: BoundingBox,
    landmarks: FaceLandmarks,
    label: str,
    color: tuple[int, int, int],
) -> None:
    import cv2

    x1 = int(round(box.x))
    y1 = int(round(box.y))
    x2 = int(round(box.x + box.width))
    y2 = int(round(box.y + box.height))
    cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
    text_y = y1 - 8 if y1 > 16 else y1 + 16
    cv2.putText(
        output,
        label,
        (x1, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv2.LINE_AA,
    )
    points = (
        (landmarks.right_eye, (255, 0, 0)),
        (landmarks.left_eye, (0, 0, 255)),
        (landmarks.nose, (0, 255, 0)),
        (landmarks.right_mouth, (255, 0, 255)),
        (landmarks.left_mouth, (0, 255, 255)),
    )
    for point, point_color in points:
        cv2.circle(output, (int(round(point.x)), int(round(point.y))), 2, point_color, -1)
