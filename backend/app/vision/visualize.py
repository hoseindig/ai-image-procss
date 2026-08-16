"""Draw face detections and tracks onto a BGR image.

Kept separate from FaceDetector, FaceTracker, quality, and alignment.
This module only renders.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from app.vision.align import AlignedFace
from app.vision.types import (
    BoundingBox,
    FaceDetection,
    FaceLandmarks,
    FaceQuality,
    FaceTrack,
    TrackState,
)


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
            [f"Face {face.confidence:.2f}"],
            (0, 255, 0),
        )
    return output


def draw_tracks(
    image: NDArray[np.uint8],
    tracks: list[FaceTrack],
    qualities: list[FaceQuality] | None = None,
) -> NDArray[np.uint8]:
    """Return a copy of `image` with track IDs, optional quality, boxes, landmarks."""
    output = np.ascontiguousarray(image.copy())
    quality_by_id = {item.track_id: item for item in qualities or []}
    for track in tracks:
        color = _track_color(track.state)
        lines = [
            f"Track #{track.track_id}",
            f"Face: {track.confidence:.2f}",
        ]
        quality = quality_by_id.get(track.track_id)
        if quality is not None:
            if quality.accepted:
                lines.append("Quality: OK")
            else:
                lines.append("Quality: REJECTED")
                reason = quality.reasons[0].value if quality.reasons else "rejected"
                lines.append(f"Reason: {reason}")
        _draw_box(output, track.bounding_box, track.landmarks, lines, color)
    return output


def compose_aligned_debug(
    camera_image: NDArray[np.uint8],
    aligned_faces: list[AlignedFace],
    *,
    panel_size: int = 224,
) -> NDArray[np.uint8]:
    """Side-by-side camera preview and real FaceAligner crops (debug only)."""
    import cv2

    base = np.ascontiguousarray(camera_image)
    if not aligned_faces:
        panel = np.zeros((panel_size, panel_size, 3), dtype=np.uint8)
        cv2.putText(
            panel,
            "No aligned face",
            (12, panel_size // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (180, 180, 180),
            1,
            cv2.LINE_AA,
        )
        return _hstack_panel(base, panel, title="Aligned Face")

    # Show the first accepted/aligned crop (typical single-user webcam).
    crop = aligned_faces[0].image
    scaled = np.asarray(
        cv2.resize(crop, (panel_size, panel_size), interpolation=cv2.INTER_NEAREST),
        dtype=np.uint8,
    )
    label = f"Track #{aligned_faces[0].source_track_id}  {crop.shape[1]}x{crop.shape[0]}"
    cv2.putText(
        scaled,
        label,
        (6, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (0, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return _hstack_panel(base, scaled, title="Aligned Face")


def _hstack_panel(
    camera_image: NDArray[np.uint8],
    panel: NDArray[np.uint8],
    *,
    title: str,
) -> NDArray[np.uint8]:
    import cv2

    height = camera_image.shape[0]
    panel_h, panel_w = panel.shape[0], panel.shape[1]
    canvas_h = max(height, panel_h + 28)
    canvas_w = camera_image.shape[1] + panel_w + 16
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    canvas[: camera_image.shape[0], : camera_image.shape[1]] = camera_image
    x0 = camera_image.shape[1] + 8
    cv2.putText(
        canvas,
        title,
        (x0, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    y0 = 28
    canvas[y0 : y0 + panel_h, x0 : x0 + panel_w] = panel
    return canvas


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
    lines: list[str],
    color: tuple[int, int, int],
) -> None:
    import cv2

    x1 = int(round(box.x))
    y1 = int(round(box.y))
    x2 = int(round(box.x + box.width))
    y2 = int(round(box.y + box.height))
    cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
    line_height = 16
    text_y = y1 - 8 - (len(lines) - 1) * line_height
    if text_y < 14:
        text_y = y1 + 16
    for index, line in enumerate(lines):
        cv2.putText(
            output,
            line,
            (x1, text_y + index * line_height),
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
