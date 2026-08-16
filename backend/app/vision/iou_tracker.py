"""IoU + centroid face tracker. No neural network; Track ID is not a person ID."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.vision.boxes import box_iou, centroid_distance
from app.vision.types import BoundingBox, FaceDetection, FaceLandmarks, FaceTrack, TrackState

logger = get_logger("app.vision")


@dataclass(frozen=True)
class TrackerConfig:
    iou_threshold: float
    max_centroid_distance: float
    max_missed_frames: int
    min_confirmed_frames: int
    max_tracks: int


@dataclass
class _Track:
    track_id: int
    bounding_box: BoundingBox
    confidence: float
    landmarks: FaceLandmarks
    age_frames: int
    missed_frames: int
    hit_count: int
    state: TrackState

    def snapshot(self) -> FaceTrack:
        return FaceTrack(
            track_id=self.track_id,
            bounding_box=self.bounding_box,
            confidence=self.confidence,
            landmarks=self.landmarks,
            age_frames=self.age_frames,
            missed_frames=self.missed_frames,
            state=self.state,
        )


class IoUCentroidFaceTracker:
    """Greedy IoU-first association with centroid-distance fallback."""

    def __init__(self, config: TrackerConfig) -> None:
        self._config = config
        self._tracks: list[_Track] = []
        self._next_id = 1
        logger.info(
            "Face tracker started iou_threshold=%.3f max_centroid_distance=%.1f "
            "max_missed_frames=%s min_confirmed_frames=%s max_tracks=%s",
            config.iou_threshold,
            config.max_centroid_distance,
            config.max_missed_frames,
            config.min_confirmed_frames,
            config.max_tracks,
        )

    def update(self, detections: list[FaceDetection]) -> list[FaceTrack]:
        assignments = _associate(self._tracks, detections, self._config)
        matched_tracks = {track_index for track_index, _det_index in assignments}
        matched_dets = {det_index for _track_index, det_index in assignments}

        for track_index, det_index in assignments:
            self._apply_match(self._tracks[track_index], detections[det_index])

        surviving: list[_Track] = []
        for index, track in enumerate(self._tracks):
            if index in matched_tracks:
                surviving.append(track)
                continue
            self._apply_miss(track)
            if track.missed_frames <= self._config.max_missed_frames:
                surviving.append(track)
            else:
                logger.debug(
                    "Track removed track_id=%s age_frames=%s",
                    track.track_id,
                    track.age_frames,
                )
        self._tracks = surviving

        unmatched = [det for index, det in enumerate(detections) if index not in matched_dets]
        unmatched.sort(
            key=lambda det: (
                -det.confidence,
                det.bounding_box.x,
                det.bounding_box.y,
                det.bounding_box.width,
            )
        )
        for detection in unmatched:
            if len(self._tracks) >= self._config.max_tracks:
                break
            created = _Track(
                track_id=self._next_id,
                bounding_box=detection.bounding_box,
                confidence=detection.confidence,
                landmarks=detection.landmarks,
                age_frames=1,
                missed_frames=0,
                hit_count=1,
                state=_state_for_hits(1, self._config.min_confirmed_frames),
            )
            self._next_id += 1
            self._tracks.append(created)
            logger.debug("Track created track_id=%s", created.track_id)

        self._tracks.sort(key=lambda item: item.track_id)
        return [track.snapshot() for track in self._tracks]

    def _apply_match(self, track: _Track, detection: FaceDetection) -> None:
        track.bounding_box = detection.bounding_box
        track.confidence = detection.confidence
        track.landmarks = detection.landmarks
        track.missed_frames = 0
        track.hit_count += 1
        track.age_frames += 1
        track.state = _state_for_hits(track.hit_count, self._config.min_confirmed_frames)

    def _apply_miss(self, track: _Track) -> None:
        track.missed_frames += 1
        track.age_frames += 1
        if track.state is TrackState.CONFIRMED:
            track.state = TrackState.LOST


def _state_for_hits(hit_count: int, min_confirmed_frames: int) -> TrackState:
    if hit_count >= min_confirmed_frames:
        return TrackState.CONFIRMED
    return TrackState.TENTATIVE


def _associate(
    tracks: list[_Track],
    detections: list[FaceDetection],
    config: TrackerConfig,
) -> list[tuple[int, int]]:
    if not tracks or not detections:
        return []
    candidates: list[tuple[int, float, float, int, int, int]] = []
    for track_index, track in enumerate(tracks):
        for det_index, detection in enumerate(detections):
            iou = box_iou(track.bounding_box, detection.bounding_box)
            distance = centroid_distance(track.bounding_box, detection.bounding_box)
            iou_ok = iou >= config.iou_threshold
            distance_ok = distance <= config.max_centroid_distance
            if not iou_ok and not distance_ok:
                continue
            iou_rank = 0 if iou_ok else 1
            candidates.append((iou_rank, -iou, distance, track.track_id, track_index, det_index))
    candidates.sort()
    used_tracks: set[int] = set()
    used_dets: set[int] = set()
    assignments: list[tuple[int, int]] = []
    for _iou_rank, _neg_iou, _distance, _track_id, track_index, det_index in candidates:
        if track_index in used_tracks or det_index in used_dets:
            continue
        used_tracks.add(track_index)
        used_dets.add(det_index)
        assignments.append((track_index, det_index))
    assignments.sort(key=lambda pair: pair[0])
    return assignments
