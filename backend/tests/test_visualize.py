from __future__ import annotations

from app.vision.types import FaceQuality, FaceTrack, QualityRejectionReason, TrackState
from app.vision.visualize import draw_detections, draw_tracks
from tests.yunet_helpers import blank_frame, sample_face


def test_draw_detections_keeps_original_shape() -> None:
    frame = blank_frame(80, 60)
    faces = [sample_face(x=10, y=8, width=20, height=24)]
    drawn = draw_detections(frame.data, faces)
    assert drawn.shape == frame.data.shape
    assert drawn is not frame.data


def test_draw_tracks_keeps_original_shape() -> None:
    frame = blank_frame(80, 60)
    face = sample_face(x=10, y=8, width=20, height=24)
    tracks = [
        FaceTrack(
            track_id=1,
            bounding_box=face.bounding_box,
            confidence=0.92,
            landmarks=face.landmarks,
            age_frames=3,
            missed_frames=0,
            state=TrackState.CONFIRMED,
        )
    ]
    drawn = draw_tracks(frame.data, tracks)
    assert drawn.shape == frame.data.shape
    assert drawn is not frame.data


def test_draw_tracks_with_quality_keeps_shape() -> None:
    frame = blank_frame(80, 60)
    face = sample_face(x=10, y=8, width=20, height=24)
    tracks = [
        FaceTrack(
            track_id=1,
            bounding_box=face.bounding_box,
            confidence=0.92,
            landmarks=face.landmarks,
            age_frames=3,
            missed_frames=0,
            state=TrackState.CONFIRMED,
        )
    ]
    qualities = [
        FaceQuality(
            track_id=1,
            accepted=False,
            reasons=[QualityRejectionReason.TOO_BLURRY],
            face_width=20,
            face_height=24,
            sharpness=1.0,
            brightness=100.0,
            landmarks_valid=True,
        )
    ]
    drawn = draw_tracks(frame.data, tracks, qualities)
    assert drawn.shape == frame.data.shape
