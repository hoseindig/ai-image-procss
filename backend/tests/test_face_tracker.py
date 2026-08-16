from __future__ import annotations

from app.vision.boxes import box_centroid, box_iou, centroid_distance
from app.vision.iou_tracker import IoUCentroidFaceTracker, TrackerConfig
from app.vision.types import FaceDetection, TrackState
from tests.yunet_helpers import sample_face


def _tracker(
    *,
    iou_threshold: float = 0.3,
    max_centroid_distance: float = 100.0,
    max_missed_frames: int = 5,
    min_confirmed_frames: int = 2,
    max_tracks: int = 20,
) -> IoUCentroidFaceTracker:
    return IoUCentroidFaceTracker(
        TrackerConfig(
            iou_threshold=iou_threshold,
            max_centroid_distance=max_centroid_distance,
            max_missed_frames=max_missed_frames,
            min_confirmed_frames=min_confirmed_frames,
            max_tracks=max_tracks,
        )
    )


def test_box_iou_and_centroid() -> None:
    left = sample_face(x=0, y=0, width=10, height=10).bounding_box
    right = sample_face(x=5, y=0, width=10, height=10).bounding_box
    assert box_iou(left, left) == 1.0
    assert box_iou(left, right) == 1.0 / 3.0
    assert box_centroid(left) == (5.0, 5.0)
    assert centroid_distance(left, right) == 5.0


def test_no_detections_yield_no_tracks() -> None:
    assert _tracker().update([]) == []


def test_one_face_creates_one_track() -> None:
    tracks = _tracker().update([sample_face(x=10, y=10, width=20, height=20)])
    assert len(tracks) == 1
    assert tracks[0].track_id == 1
    assert tracks[0].state is TrackState.TENTATIVE
    assert tracks[0].age_frames == 1
    assert tracks[0].missed_frames == 0


def test_same_face_keeps_track_id() -> None:
    tracker = _tracker()
    first = tracker.update([sample_face(x=10, y=10, width=20, height=20)])
    second = tracker.update([sample_face(x=12, y=11, width=20, height=20)])
    assert first[0].track_id == second[0].track_id == 1
    assert second[0].state is TrackState.CONFIRMED


def test_face_movement_keeps_track_id() -> None:
    tracker = _tracker()
    ids: list[int] = []
    for step in range(8):
        tracks = tracker.update(
            [sample_face(x=20 + step * 6, y=30, width=24, height=24, confidence=0.9)]
        )
        assert len(tracks) == 1
        ids.append(tracks[0].track_id)
    assert ids == [1] * 8


def test_temporary_missing_detection_survives() -> None:
    tracker = _tracker(max_missed_frames=5)
    tracker.update([sample_face(x=40, y=40, width=20, height=20)])
    tracker.update([sample_face(x=41, y=40, width=20, height=20)])
    missing = tracker.update([])
    assert len(missing) == 1
    assert missing[0].track_id == 1
    assert missing[0].state is TrackState.LOST
    returned = tracker.update([sample_face(x=42, y=41, width=20, height=20)])
    assert len(returned) == 1
    assert returned[0].track_id == 1
    assert returned[0].state is TrackState.CONFIRMED
    assert returned[0].missed_frames == 0


def test_long_disappearance_removes_track() -> None:
    tracker = _tracker(max_missed_frames=2)
    tracker.update([sample_face(x=10, y=10, width=20, height=20)])
    tracker.update([sample_face(x=10, y=10, width=20, height=20)])
    assert len(tracker.update([])) == 1
    assert len(tracker.update([])) == 1
    assert tracker.update([]) == []


def test_new_face_gets_new_track_id() -> None:
    tracker = _tracker()
    tracker.update([sample_face(x=10, y=10, width=20, height=20)])
    tracker.update([sample_face(x=10, y=10, width=20, height=20)])
    both = tracker.update(
        [
            sample_face(x=10, y=10, width=20, height=20),
            sample_face(x=200, y=10, width=20, height=20),
        ]
    )
    ids = sorted(track.track_id for track in both)
    assert ids == [1, 2]


def test_multiple_faces_keep_independent_ids() -> None:
    tracker = _tracker()
    for step in range(5):
        tracks = tracker.update(
            [
                sample_face(x=10 + step, y=10, width=20, height=20, confidence=0.91),
                sample_face(x=200 + step, y=12, width=20, height=20, confidence=0.88),
            ]
        )
        by_x = sorted(tracks, key=lambda item: item.bounding_box.x)
        assert [item.track_id for item in by_x] == [1, 2]


def test_close_faces_remain_deterministic() -> None:
    tracker = _tracker(iou_threshold=0.3, max_centroid_distance=80)
    first = tracker.update(
        [
            sample_face(x=0, y=0, width=40, height=40, confidence=0.95),
            sample_face(x=50, y=0, width=40, height=40, confidence=0.90),
        ]
    )
    second = tracker.update(
        [
            sample_face(x=4, y=0, width=40, height=40, confidence=0.94),
            sample_face(x=54, y=0, width=40, height=40, confidence=0.89),
        ]
    )
    assert [track.track_id for track in first] == [track.track_id for track in second]


def test_crossing_faces_follow_greedy_iou() -> None:
    """IoU tracking follows boxes, not identity. Heavy overlap can swap IDs."""
    tracker = _tracker(iou_threshold=0.2, max_centroid_distance=30)
    tracker.update(
        [
            sample_face(x=0, y=0, width=40, height=40, confidence=0.95),
            sample_face(x=80, y=0, width=40, height=40, confidence=0.90),
        ]
    )
    crossed = tracker.update(
        [
            sample_face(x=80, y=0, width=40, height=40, confidence=0.95),
            sample_face(x=0, y=0, width=40, height=40, confidence=0.90),
        ]
    )
    left = next(track for track in crossed if track.bounding_box.x == 0)
    right = next(track for track in crossed if track.bounding_box.x == 80)
    assert left.track_id == 1
    assert right.track_id == 2


def test_confidence_change_does_not_reset_id() -> None:
    tracker = _tracker()
    first = tracker.update([sample_face(x=10, y=10, width=20, height=20, confidence=0.95)])
    second = tracker.update([sample_face(x=10, y=10, width=20, height=20, confidence=0.71)])
    assert first[0].track_id == second[0].track_id
    assert second[0].confidence == 0.71


def test_lifecycle_tentative_confirmed_lost_removed() -> None:
    tracker = _tracker(min_confirmed_frames=2, max_missed_frames=1)
    tentative = tracker.update([sample_face(x=8, y=8, width=16, height=16)])
    assert tentative[0].state is TrackState.TENTATIVE
    confirmed = tracker.update([sample_face(x=8, y=8, width=16, height=16)])
    assert confirmed[0].state is TrackState.CONFIRMED
    lost = tracker.update([])
    assert lost[0].state is TrackState.LOST
    assert lost[0].track_id == 1
    assert tracker.update([]) == []


def test_max_tracks_is_respected() -> None:
    tracker = _tracker(max_tracks=2)
    tracks = tracker.update(
        [
            sample_face(x=0, y=0, width=10, height=10, confidence=0.99),
            sample_face(x=40, y=0, width=10, height=10, confidence=0.90),
            sample_face(x=80, y=0, width=10, height=10, confidence=0.80),
        ]
    )
    assert len(tracks) == 2
    assert [track.track_id for track in tracks] == [1, 2]


def test_same_sequence_is_deterministic() -> None:
    sequence = [
        [
            sample_face(x=10, y=10, width=20, height=20),
            sample_face(x=120, y=10, width=20, height=20),
        ],
        [
            sample_face(x=12, y=10, width=20, height=20),
            sample_face(x=122, y=11, width=20, height=20),
        ],
        [],
        [sample_face(x=14, y=10, width=20, height=20)],
    ]
    first = _ids_for_sequence(sequence)
    second = _ids_for_sequence(sequence)
    assert first == second


def _ids_for_sequence(sequence: list[list[FaceDetection]]) -> list[list[int]]:
    tracker = _tracker()
    result: list[list[int]] = []
    for detections in sequence:
        tracks = tracker.update(detections)
        result.append([track.track_id for track in tracks])
    return result
