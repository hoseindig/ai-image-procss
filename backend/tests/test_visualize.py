from __future__ import annotations

from app.vision.visualize import draw_detections
from tests.yunet_helpers import blank_frame, sample_face


def test_draw_detections_keeps_original_shape() -> None:
    frame = blank_frame(80, 60)
    faces = [sample_face(x=10, y=8, width=20, height=24)]
    drawn = draw_detections(frame.data, faces)
    assert drawn.shape == frame.data.shape
    assert drawn is not frame.data
