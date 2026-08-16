"""Camera API service. Routes stay thin; lifecycle lives in CameraManager."""

from __future__ import annotations

from app.cameras.manager import CameraManager
from app.cameras.types import CameraStatus


class CameraService:
    def __init__(self, manager: CameraManager) -> None:
        self._manager = manager

    def list_cameras(self) -> list[CameraStatus]:
        return self._manager.list_status()

    def get_camera(self, camera_id: str) -> CameraStatus:
        return self._manager.get_status(camera_id)

    def start_camera(self, camera_id: str) -> CameraStatus:
        return self._manager.start(camera_id)

    def stop_camera(self, camera_id: str) -> CameraStatus:
        self._manager.stop(camera_id)
        return self._manager.close(camera_id)
