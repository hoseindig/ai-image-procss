"""Unit tests for face quality assessment and landmark alignment."""

from __future__ import annotations

import numpy as np

from app.vision.align import (
    ALIGNMENT_LANDMARK_TOLERANCE_PX,
    AlignConfig,
    LandmarkFaceAligner,
    apply_affine_to_points,
    landmark_targets,
)
from app.vision.quality import HeuristicFaceQualityAssessor, QualityConfig
from app.vision.types import FaceLandmarks, Point, QualityRejectionReason
from tests.quality_helpers import (
    collapsed_landmarks,
    solid_face_frame,
    textured_frame,
    track_from_box,
)


def _assessor(
    *,
    min_face_width: float = 80.0,
    min_face_height: float = 80.0,
    min_sharpness: float = 60.0,
    min_brightness: float = 40.0,
    max_brightness: float = 220.0,
) -> HeuristicFaceQualityAssessor:
    return HeuristicFaceQualityAssessor(
        QualityConfig(
            min_face_width=min_face_width,
            min_face_height=min_face_height,
            min_sharpness=min_sharpness,
            min_brightness=min_brightness,
            max_brightness=max_brightness,
        )
    )


def test_good_face_is_accepted() -> None:
    box = (40, 40, 100, 100)
    frame = textured_frame(320, 240, face_box=box)
    track = track_from_box(x=40, y=40, width=100, height=100)
    quality = _assessor().assess(frame, track)
    assert quality.accepted is True
    assert quality.reasons == []
    assert quality.landmarks_valid is True
    assert quality.sharpness is not None and quality.sharpness >= 60.0
    assert quality.brightness is not None


def test_face_too_small() -> None:
    box = (10, 10, 40, 40)
    frame = textured_frame(160, 120, face_box=box)
    track = track_from_box(x=10, y=10, width=40, height=40)
    quality = _assessor().assess(frame, track)
    assert quality.accepted is False
    assert QualityRejectionReason.FACE_TOO_SMALL in quality.reasons


def test_blurry_face() -> None:
    box = (40, 40, 100, 100)
    frame = textured_frame(320, 240, face_box=box, blur_face=True)
    track = track_from_box(x=40, y=40, width=100, height=100)
    quality = _assessor(min_sharpness=60.0).assess(frame, track)
    assert quality.accepted is False
    assert QualityRejectionReason.TOO_BLURRY in quality.reasons


def test_too_dark() -> None:
    box = (40, 40, 100, 100)
    frame = solid_face_frame(320, 240, face_box=box, value=10)
    track = track_from_box(x=40, y=40, width=100, height=100)
    quality = _assessor(min_sharpness=0.0).assess(frame, track)
    assert quality.accepted is False
    assert QualityRejectionReason.TOO_DARK in quality.reasons


def test_too_bright() -> None:
    box = (40, 40, 100, 100)
    frame = solid_face_frame(320, 240, face_box=box, value=250)
    track = track_from_box(x=40, y=40, width=100, height=100)
    quality = _assessor(min_sharpness=0.0).assess(frame, track)
    assert quality.accepted is False
    assert QualityRejectionReason.TOO_BRIGHT in quality.reasons


def test_invalid_landmarks() -> None:
    box = (40, 40, 100, 100)
    frame = textured_frame(320, 240, face_box=box)
    track = track_from_box(
        x=40,
        y=40,
        width=100,
        height=100,
        landmarks=collapsed_landmarks(x=40, y=40, width=100, height=100),
    )
    quality = _assessor(min_sharpness=0.0).assess(frame, track)
    assert quality.accepted is False
    assert quality.landmarks_valid is False
    assert QualityRejectionReason.INVALID_LANDMARKS in quality.reasons


def test_invalid_crop() -> None:
    frame = textured_frame(160, 120)
    track = track_from_box(x=200, y=10, width=100, height=100)
    quality = _assessor(min_sharpness=0.0, min_face_width=10, min_face_height=10).assess(
        frame, track
    )
    assert quality.accepted is False
    assert QualityRejectionReason.INVALID_CROP in quality.reasons


def test_alignment_output_size_and_determinism() -> None:
    box = (50, 40, 120, 120)
    frame = textured_frame(400, 300, face_box=box)
    track = track_from_box(x=50, y=40, width=120, height=120)
    aligner = LandmarkFaceAligner(AlignConfig(output_width=112, output_height=112))
    first = aligner.align(frame, track)
    second = aligner.align(frame, track)
    assert first.width == 112
    assert first.height == 112
    assert first.image.shape == (112, 112, 3)
    assert first.source_track_id == 1
    assert np.array_equal(first.image, second.image)
    assert np.allclose(first.transform, second.transform)


def test_alignment_maps_landmarks_near_targets() -> None:
    """Transformed source landmarks should land near ArcFace targets (±2 px)."""
    targets = landmark_targets(112, 112)
    # Place source landmarks exactly at a known similarity of the template.
    scale = 2.0
    offset_x = 30.0
    offset_y = 20.0
    source_pts = targets * scale + np.array([offset_x, offset_y])
    landmarks = FaceLandmarks(
        left_eye=Point(x=float(source_pts[0, 0]), y=float(source_pts[0, 1])),
        right_eye=Point(x=float(source_pts[1, 0]), y=float(source_pts[1, 1])),
        nose=Point(x=float(source_pts[2, 0]), y=float(source_pts[2, 1])),
        left_mouth=Point(x=float(source_pts[3, 0]), y=float(source_pts[3, 1])),
        right_mouth=Point(x=float(source_pts[4, 0]), y=float(source_pts[4, 1])),
    )
    xs = source_pts[:, 0]
    ys = source_pts[:, 1]
    track = track_from_box(
        x=float(xs.min() - 10),
        y=float(ys.min() - 10),
        width=float(xs.max() - xs.min() + 20),
        height=float(ys.max() - ys.min() + 20),
        landmarks=landmarks,
    )
    frame = textured_frame(
        400, 400, face_box=(int(track.bounding_box.x), int(track.bounding_box.y), 200, 200)
    )
    aligner = LandmarkFaceAligner(AlignConfig(output_width=112, output_height=112))
    aligned = aligner.align(frame, track)
    mapped = apply_affine_to_points(source_pts, aligned.transform)
    assert mapped.shape == targets.shape
    max_err = float(np.max(np.linalg.norm(mapped - targets, axis=1)))
    assert max_err <= ALIGNMENT_LANDMARK_TOLERANCE_PX


def test_alignment_different_positions_remain_geometric() -> None:
    aligner = LandmarkFaceAligner(AlignConfig(output_width=112, output_height=112))
    targets = landmark_targets(112, 112)
    for offset in ((10.0, 15.0), (80.0, 40.0), (120.0, 90.0)):
        source_pts = targets * 1.5 + np.array(offset)
        landmarks = FaceLandmarks(
            left_eye=Point(x=float(source_pts[0, 0]), y=float(source_pts[0, 1])),
            right_eye=Point(x=float(source_pts[1, 0]), y=float(source_pts[1, 1])),
            nose=Point(x=float(source_pts[2, 0]), y=float(source_pts[2, 1])),
            left_mouth=Point(x=float(source_pts[3, 0]), y=float(source_pts[3, 1])),
            right_mouth=Point(x=float(source_pts[4, 0]), y=float(source_pts[4, 1])),
        )
        track = track_from_box(
            x=float(source_pts[:, 0].min() - 5),
            y=float(source_pts[:, 1].min() - 5),
            width=120,
            height=120,
            landmarks=landmarks,
        )
        frame = textured_frame(500, 400)
        aligned = aligner.align(frame, track)
        mapped = apply_affine_to_points(source_pts, aligned.transform)
        max_err = float(np.max(np.linalg.norm(mapped - targets, axis=1)))
        assert max_err <= ALIGNMENT_LANDMARK_TOLERANCE_PX


def test_multiple_tracks_assessed_independently() -> None:
    frame = textured_frame(
        400,
        240,
        face_box=(30, 40, 100, 100),
    )
    # Second face region painted dark solid → rejected for darkness / blur.
    frame.data[40:140, 220:320] = 8
    good = track_from_box(track_id=1, x=30, y=40, width=100, height=100)
    bad = track_from_box(track_id=2, x=220, y=40, width=100, height=100)
    assessor = _assessor(min_sharpness=0.0)
    q1 = assessor.assess(frame, good)
    q2 = assessor.assess(frame, bad)
    assert q1.accepted is True
    assert q2.accepted is False
    assert q1.track_id == 1
    assert q2.track_id == 2


def test_factory_disabled_quality_and_alignment(settings: object) -> None:
    from app.core.config import Settings
    from app.vision.factory import create_face_aligner, create_face_quality_assessor

    assert isinstance(settings, Settings)
    disabled_quality = settings.model_copy(update={"face_quality_enabled": False})
    disabled_align = settings.model_copy(update={"face_alignment_enabled": False})
    assert create_face_quality_assessor(disabled_quality) is None
    assert create_face_aligner(disabled_align) is None
    enabled = settings.model_copy(
        update={"face_quality_enabled": True, "face_alignment_enabled": True}
    )
    assert create_face_quality_assessor(enabled) is not None
    assert create_face_aligner(enabled) is not None


def test_aligner_respects_configurable_output_size() -> None:
    frame = textured_frame(300, 300, face_box=(40, 40, 120, 120))
    track = track_from_box(x=40, y=40, width=120, height=120)
    aligner = LandmarkFaceAligner(AlignConfig(output_width=96, output_height=96))
    aligned = aligner.align(frame, track)
    assert aligned.image.shape == (96, 96, 3)
    assert aligned.width == 96
    assert aligned.height == 96
