from __future__ import annotations

from app.vision.geometry import CoordinateMapper, clip_detection, padded_size
from app.vision.types import BoundingBox, FaceDetection, FaceLandmarks, Point


def test_mapper_scales_from_model_input_to_original_frame() -> None:
    mapper = CoordinateMapper(
        original_width=1280,
        original_height=720,
        input_width=320,
        input_height=320,
    )
    box = mapper.box(80.0, 40.0, 60.0, 80.0)
    assert box.x == 320.0
    assert box.y == 90.0
    assert box.width == 240.0
    assert box.height == 180.0
    point = mapper.point(160.0, 80.0)
    assert point.x == 640.0
    assert point.y == 180.0


def test_mapper_is_identity_when_sizes_match() -> None:
    mapper = CoordinateMapper(
        original_width=640,
        original_height=480,
        input_width=640,
        input_height=480,
    )
    box = mapper.box(10.0, 20.0, 30.0, 40.0)
    assert box.x == 10.0
    assert box.y == 20.0
    assert box.width == 30.0
    assert box.height == 40.0


def test_padding_is_bottom_right_and_does_not_shift_origin() -> None:
    pad_width, pad_height = padded_size(300, 300)
    assert pad_width == 320
    assert pad_height == 320
    mapper = CoordinateMapper(
        original_width=600,
        original_height=300,
        input_width=300,
        input_height=300,
    )
    # A detection at the origin of the resized image stays at the original origin.
    origin = mapper.point(0.0, 0.0)
    assert origin.x == 0.0
    assert origin.y == 0.0


def test_clip_detection_stays_inside_original_frame() -> None:
    detection = FaceDetection(
        bounding_box=BoundingBox(x=-10.0, y=-5.0, width=50.0, height=40.0),
        confidence=0.9,
        landmarks=FaceLandmarks(
            left_eye=Point(x=-1.0, y=2.0),
            right_eye=Point(x=80.0, y=2.0),
            nose=Point(x=20.0, y=20.0),
            left_mouth=Point(x=10.0, y=30.0),
            right_mouth=Point(x=30.0, y=30.0),
        ),
    )
    clipped = clip_detection(detection, width=64, height=48)
    assert clipped.bounding_box.x == 0.0
    assert clipped.bounding_box.y == 0.0
    assert clipped.bounding_box.width == 40.0
    assert clipped.bounding_box.height == 35.0
    assert clipped.landmarks.left_eye.x == 0.0
    assert clipped.landmarks.right_eye.x == 64.0
