"""Camera API service. Routes stay thin; lifecycle lives in CameraManager."""

from __future__ import annotations

from app.cameras.manager import CameraManager
from app.cameras.types import CameraStatus
from app.vision.runtime import DetectionRuntime


class CameraService:
    def __init__(self, manager: CameraManager, detection_runtime: DetectionRuntime) -> None:
        self._manager = manager
        self._detection = detection_runtime

    def list_cameras(self) -> list[CameraStatus]:
        return self._manager.list_status()

    def get_camera(self, camera_id: str) -> CameraStatus:
        return self._manager.get_status(camera_id)

    def start_camera(self, camera_id: str) -> CameraStatus:
        status = self._manager.start(camera_id)
        self._detection.attach(camera_id)
        return status

    def stop_camera(self, camera_id: str) -> CameraStatus:
        self._detection.detach(camera_id)
        self._manager.stop(camera_id)
        return self._manager.close(camera_id)
