"""Face detection API service. Routes stay thin."""

from __future__ import annotations

from app.cameras.manager import CameraManager
from app.schemas.detection import DetectionResponse, FaceDetectionDto, FaceQualityDto, FaceTrackDto
from app.vision.runtime import DetectionRuntime
from app.vision.types import DetectionSnapshot, FaceQuality


class DetectionService:
    def __init__(self, manager: CameraManager, runtime: DetectionRuntime) -> None:
        self._manager = manager
        self._runtime = runtime

    def get_detections(self, camera_id: str) -> DetectionResponse:
        self._manager.get_status(camera_id)
        snapshot = self._runtime.latest(camera_id)
        return _to_response(camera_id, self._runtime.enabled, snapshot)


def _to_response(
    camera_id: str,
    enabled: bool,
    snapshot: DetectionSnapshot | None,
) -> DetectionResponse:
    if snapshot is None:
        return DetectionResponse(camera_id=camera_id, enabled=enabled)
    quality_by_id = {item.track_id: item for item in snapshot.qualities}
    aligned_ids = set(snapshot.aligned_track_ids)
    return DetectionResponse(
        camera_id=camera_id,
        enabled=enabled,
        timestamp=snapshot.timestamp,
        faces=[
            FaceDetectionDto(
                confidence=face.confidence,
                bounding_box=face.bounding_box,
                landmarks=face.landmarks,
            )
            for face in snapshot.faces
        ],
        tracks=[
            FaceTrackDto(
                track_id=track.track_id,
                state=track.state,
                confidence=track.confidence,
                bounding_box=track.bounding_box,
                landmarks=track.landmarks,
                age_frames=track.age_frames,
                missed_frames=track.missed_frames,
                quality=_quality_dto(
                    quality_by_id.get(track.track_id),
                    track.track_id in aligned_ids,
                ),
            )
            for track in snapshot.tracks
        ],
        inference_ms=snapshot.inference_ms,
        tracking_ms=snapshot.tracking_ms,
        quality_ms=snapshot.quality_ms,
        alignment_ms=snapshot.alignment_ms,
        aligned_count=snapshot.aligned_count,
        error=snapshot.error,
    )


def _quality_dto(quality: FaceQuality | None, aligned: bool) -> FaceQualityDto | None:
    if quality is None:
        return None
    return FaceQualityDto(
        accepted=quality.accepted,
        reasons=list(quality.reasons),
        face_width=quality.face_width,
        face_height=quality.face_height,
        sharpness=quality.sharpness,
        brightness=quality.brightness,
        landmarks_valid=quality.landmarks_valid,
        aligned=aligned,
    )
