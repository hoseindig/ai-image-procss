"""In-process camera registry. Holds sources by ID; no global singleton."""

from __future__ import annotations

import threading
from collections.abc import Callable

from app.cameras.exceptions import CameraInvalidStateError, CameraNotFoundError, CameraOpenError
from app.cameras.source import CameraSource
from app.cameras.types import CameraConfig, CameraState, CameraStatus, SourceType
from app.cameras.usb import UsbCameraSource
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger("app.camera")

SourceFactory = Callable[[CameraConfig], CameraSource]


def config_from_settings(settings: Settings) -> CameraConfig:
    return CameraConfig(
        camera_id=settings.camera_default_id,
        name=settings.camera_default_name,
        source_type=SourceType.USB,
        device_index=settings.camera_device_index,
        enabled=True,
        width=settings.camera_width,
        height=settings.camera_height,
        fps=settings.camera_fps,
        backend=settings.camera_backend,
    )


def default_source_factory(config: CameraConfig) -> CameraSource:
    if config.source_type is SourceType.USB:
        return UsbCameraSource(config)
    raise CameraOpenError(f"Source type '{config.source_type}' is not implemented in this version")


class CameraManager:
    """Owns CameraSource instances keyed by camera_id."""

    def __init__(self, source_factory: SourceFactory | None = None) -> None:
        self._factory = source_factory or default_source_factory
        self._lock = threading.RLock()
        self._sources: dict[str, CameraSource] = {}

    def register(self, config: CameraConfig) -> CameraStatus:
        if not config.enabled:
            raise CameraInvalidStateError(f"Camera '{config.camera_id}' is disabled")
        with self._lock:
            existing = self._sources.get(config.camera_id)
            if existing is not None:
                if existing.is_open() or existing.is_running():
                    raise CameraInvalidStateError(
                        f"Camera '{config.camera_id}' is already registered and open"
                    )
                raise CameraInvalidStateError(f"Camera '{config.camera_id}' is already registered")
            source = self._factory(config)
            self._sources[config.camera_id] = source
            logger.info("Registered camera id=%s type=%s", config.camera_id, config.source_type)
            return source.get_status()

    def start(self, camera_id: str) -> CameraStatus:
        source = self._get(camera_id)
        if not source.is_open():
            source.open()
        source.start()
        return source.get_status()

    def stop(self, camera_id: str) -> CameraStatus:
        source = self._get(camera_id)
        source.stop()
        return source.get_status()

    def close(self, camera_id: str) -> CameraStatus:
        source = self._get(camera_id)
        source.close()
        return source.get_status()

    def open(self, camera_id: str) -> CameraStatus:
        source = self._get(camera_id)
        source.open()
        return source.get_status()

    def get_status(self, camera_id: str) -> CameraStatus:
        return self._get(camera_id).get_status()

    def list_status(self) -> list[CameraStatus]:
        with self._lock:
            sources = list(self._sources.values())
        return [source.get_status() for source in sources]

    def get_source(self, camera_id: str) -> CameraSource:
        return self._get(camera_id)

    def shutdown(self) -> None:
        with self._lock:
            sources = list(self._sources.items())
        for camera_id, source in sources:
            try:
                source.close()
            except Exception:
                logger.exception("Error shutting down camera %s", camera_id)

    def summary(self) -> tuple[bool, bool]:
        """Return (available, running) for system status. Does not probe hardware."""
        statuses = self.list_status()
        if not statuses:
            return False, False
        available = any(item.state is not CameraState.ERROR for item in statuses)
        running = any(item.state is CameraState.RUNNING for item in statuses)
        return available, running

    def _get(self, camera_id: str) -> CameraSource:
        with self._lock:
            source = self._sources.get(camera_id)
        if source is None:
            raise CameraNotFoundError(camera_id)
        return source
