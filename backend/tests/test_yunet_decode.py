from __future__ import annotations

import math

from app.vision.decode import RawFace, decode_yunet, nms
from tests.yunet_helpers import empty_yunet_outputs, set_anchor_score, yunet_outputs_with_faces


def test_decode_no_faces() -> None:
    outputs = empty_yunet_outputs(320, 320)
    faces = decode_yunet(
        outputs,
        pad_width=320,
        pad_height=320,
        score_threshold=0.7,
        nms_threshold=0.3,
        max_faces=10,
    )
    assert faces == []


def test_decode_one_face_and_five_landmarks() -> None:
    outputs = yunet_outputs_with_faces(320, 320, [(8, 5, 5)])
    faces = decode_yunet(
        outputs,
        pad_width=320,
        pad_height=320,
        score_threshold=0.7,
        nms_threshold=0.3,
        max_faces=10,
    )
    assert len(faces) == 1
    face = faces[0]
    assert face.confidence == 1.0
    assert face.width == 8.0
    assert face.height == 8.0
    assert face.x == 36.0
    assert face.y == 36.0
    assert face.right_eye_x == 40.0
    assert face.right_eye_y == 40.0
    assert face.left_eye_x == 40.0
    assert face.left_eye_y == 40.0
    assert face.nose_x == 40.0
    assert face.nose_y == 40.0
    assert face.right_mouth_x == 40.0
    assert face.right_mouth_y == 40.0
    assert face.left_mouth_x == 40.0
    assert face.left_mouth_y == 40.0


def test_decode_multiple_faces() -> None:
    outputs = yunet_outputs_with_faces(320, 320, [(8, 2, 2), (8, 20, 20)])
    faces = decode_yunet(
        outputs,
        pad_width=320,
        pad_height=320,
        score_threshold=0.7,
        nms_threshold=0.3,
        max_faces=10,
    )
    assert len(faces) == 2


def test_confidence_threshold_filters_low_scores() -> None:
    outputs = empty_yunet_outputs(320, 320)
    set_anchor_score(outputs, stride=8, row=4, col=4, width=320, height=320, cls=1.0, obj=1.0)
    set_anchor_score(outputs, stride=8, row=10, col=10, width=320, height=320, cls=0.25, obj=0.25)
    faces = decode_yunet(
        outputs,
        pad_width=320,
        pad_height=320,
        score_threshold=0.7,
        nms_threshold=0.3,
        max_faces=10,
    )
    assert len(faces) == 1
    assert faces[0].confidence == 1.0
    low = math.sqrt(0.25 * 0.25)
    assert low < 0.7


def test_max_faces_is_applied_after_nms() -> None:
    outputs = yunet_outputs_with_faces(320, 320, [(8, 1, 1), (8, 8, 8), (8, 16, 16)])
    faces = decode_yunet(
        outputs,
        pad_width=320,
        pad_height=320,
        score_threshold=0.7,
        nms_threshold=0.3,
        max_faces=2,
    )
    assert len(faces) == 2


def test_nms_drops_overlapping_lower_score() -> None:
    high = RawFace(
        x=0,
        y=0,
        width=10,
        height=10,
        confidence=0.95,
        right_eye_x=1,
        right_eye_y=1,
        left_eye_x=2,
        left_eye_y=1,
        nose_x=1.5,
        nose_y=2,
        right_mouth_x=2,
        right_mouth_y=3,
        left_mouth_x=1,
        left_mouth_y=3,
    )
    low = RawFace(
        x=1,
        y=1,
        width=10,
        height=10,
        confidence=0.8,
        right_eye_x=1,
        right_eye_y=1,
        left_eye_x=2,
        left_eye_y=1,
        nose_x=1.5,
        nose_y=2,
        right_mouth_x=2,
        right_mouth_y=3,
        left_mouth_x=1,
        left_mouth_y=3,
    )
    kept = nms([high, low], iou_threshold=0.3, max_faces=10)
    assert kept == [high]
