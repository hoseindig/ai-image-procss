"""Fake CameraSource for tests. Does not open hardware or import OpenCV."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
from numpy.typing import NDArray

from app.cameras.exceptions import (
    CameraAlreadyRunningError,
    CameraInvalidStateError,
    CameraNotAvailableError,
    CameraOpenError,
    CameraReadError,
)
from app.cameras.types import CameraConfig, CameraState, CameraStatus, Frame


class FakeCameraSource:
    def __init__(
        self,
        config: CameraConfig,
        *,
        unavailable: bool = False,
        fail_open: bool = False,
        fail_read: bool = False,
    ) -> None:
        self._config = config
        self._unavailable = unavailable
        self._fail_open = fail_open
        self._fail_read = fail_read
        self._state = CameraState.CLOSED
        self._error: str | None = None
        self._last_frame_at: datetime | None = None
        self._frame: Frame | None = None
        self._custom_data: NDArray[np.uint8] | None = None
        self.open_count = 0
        self.close_count = 0

    def set_frame_data(self, data: NDArray[np.uint8]) -> None:
        self._custom_data = data

    def open(self) -> None:
        if self._state in {CameraState.OPEN, CameraState.RUNNING, CameraState.STOPPED}:
            raise CameraInvalidStateError(f"Camera '{self._config.camera_id}' is already open")
        self.open_count += 1
        if self._unavailable:
            self._state = CameraState.ERROR
            self._error = "Camera is not available"
            raise CameraNotAvailableError(self._error)
        if self._fail_open:
            self._state = CameraState.ERROR
            self._error = "Failed to open camera"
            raise CameraOpenError(self._error)
        self._error = None
        self._state = CameraState.OPEN
        self._frame = self._make_frame()

    def start(self) -> None:
        if self._state == CameraState.RUNNING:
            raise CameraAlreadyRunningError(self._config.camera_id)
        if self._state not in {CameraState.OPEN, CameraState.STOPPED}:
            raise CameraInvalidStateError(
                f"Camera '{self._config.camera_id}' must be open before start"
            )
        self._state = CameraState.RUNNING

    def read(self) -> Frame | None:
        if self._state == CameraState.ERROR:
            raise CameraReadError(self._error or "Camera read failed")
        if self._state != CameraState.RUNNING:
            raise CameraInvalidStateError(f"Camera '{self._config.camera_id}' is not running")
        if self._fail_read:
            self._state = CameraState.ERROR
            self._error = "Camera read failed"
            raise CameraReadError(self._error)
        self._frame = self._make_frame()
        return self._frame

    def stop(self) -> None:
        if self._state == CameraState.ERROR:
            # Mirror USB: allow stop after read failure so close can follow.
            return
        if self._state != CameraState.RUNNING:
            raise CameraInvalidStateError(f"Camera '{self._config.camera_id}' is not running")
        self._state = CameraState.STOPPED

    def close(self) -> None:
        if self._state == CameraState.CLOSED:
            return
        self.close_count += 1
        self._state = CameraState.CLOSED
        self._frame = None

    def is_open(self) -> bool:
        return self._state in {CameraState.OPEN, CameraState.RUNNING, CameraState.STOPPED}

    def is_running(self) -> bool:
        return self._state == CameraState.RUNNING

    def get_status(self) -> CameraStatus:
        return CameraStatus(
            id=self._config.camera_id,
            name=self._config.name,
            state=self._state,
            device_index=self._config.device_index,
            width=self._config.width,
            height=self._config.height,
            fps=self._config.fps,
            last_frame_at=self._last_frame_at,
            error=self._error,
        )

    def _make_frame(self) -> Frame:
        timestamp = datetime.now(UTC)
        self._last_frame_at = timestamp
        if self._custom_data is not None:
            data = np.ascontiguousarray(self._custom_data.copy())
            height, width = int(data.shape[0]), int(data.shape[1])
        else:
            data = np.zeros((self._config.height, self._config.width, 3), dtype=np.uint8)
            height, width = self._config.height, self._config.width
        return Frame(
            data=data,
            timestamp=timestamp,
            width=width,
            height=height,
        )
