"""Face detection API service. Routes stay thin."""

from __future__ import annotations

from app.cameras.manager import CameraManager
from app.schemas.detection import DetectionResponse, FaceDetectionDto
from app.vision.runtime import DetectionRuntime
from app.vision.types import DetectionSnapshot


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
        inference_ms=snapshot.inference_ms,
        error=snapshot.error,
    )
