"""USB webcam source. OpenCV is confined to this module."""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from app.cameras.buffer import LatestFrameSlot
from app.cameras.exceptions import (
    CameraAlreadyRunningError,
    CameraError,
    CameraInvalidStateError,
    CameraNotAvailableError,
    CameraOpenError,
    CameraReadError,
)
from app.cameras.types import CameraConfig, CameraState, CameraStatus, Frame
from app.core.logging import get_logger

logger = get_logger("app.camera")

_MAX_CONSECUTIVE_READ_FAILURES = 30
_THREAD_JOIN_TIMEOUT_SECONDS = 5.0


class VideoCaptureLike(Protocol):
    """Minimal capture surface. Implemented by cv2.VideoCapture in production."""

    def isOpened(self) -> bool:  # noqa: N802
        ...

    def read(self) -> tuple[bool, NDArray[np.uint8] | None]: ...

    def release(self) -> None: ...

    def set(self, prop_id: int, value: float) -> bool: ...

    def get(self, prop_id: int) -> float: ...


CaptureOpener = Callable[[int, int], VideoCaptureLike]


def _opencv_opener(device_index: int, api_preference: int) -> VideoCaptureLike:
    import cv2

    # OpenCV's VideoCapture.read overloads are wider than VideoCaptureLike.
    return cv2.VideoCapture(device_index, api_preference)  # type: ignore[return-value]


def _api_preference(backend: str) -> int:
    import cv2

    mapping = {
        "dshow": int(getattr(cv2, "CAP_DSHOW", cv2.CAP_ANY)),
        "msmf": int(getattr(cv2, "CAP_MSMF", cv2.CAP_ANY)),
        "any": int(cv2.CAP_ANY),
    }
    return mapping.get(backend, int(cv2.CAP_ANY))


def _fallback_preferences(preferred: str) -> list[int]:
    import cv2

    primary = _api_preference(preferred)
    extras: list[int] = []
    if sys.platform == "win32":
        for name in ("dshow", "msmf", "any"):
            value = _api_preference(name)
            if value not in extras and value != primary:
                extras.append(value)
    else:
        any_pref = int(cv2.CAP_ANY)
        if any_pref != primary:
            extras.append(any_pref)
    return [primary, *extras]


class UsbCameraSource:
    """CameraSource backed by a local USB device via OpenCV VideoCapture."""

    def __init__(
        self,
        config: CameraConfig,
        *,
        opener: CaptureOpener | None = None,
    ) -> None:
        self._config = config
        self._opener = opener or _opencv_opener
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._capture: VideoCaptureLike | None = None
        self._state = CameraState.CLOSED
        self._error: str | None = None
        self._actual_width = config.width
        self._actual_height = config.height
        self._actual_fps = config.fps
        self._last_frame_at: datetime | None = None
        self._frames = LatestFrameSlot()

    def open(self) -> None:
        with self._lock:
            if self._state in {CameraState.OPEN, CameraState.RUNNING, CameraState.STOPPED}:
                raise CameraInvalidStateError(f"Camera '{self._config.camera_id}' is already open")
            self._state = CameraState.OPENING
            self._error = None
            logger.info(
                "Opening USB camera id=%s index=%s requested=%sx%s@%s",
                self._config.camera_id,
                self._config.device_index,
                self._config.width,
                self._config.height,
                self._config.fps,
            )
            try:
                capture = self._open_device()
                self._configure_capture(capture)
                self._verify_capture(capture)
                self._capture = capture
                self._state = CameraState.OPEN
                logger.info(
                    "USB camera opened id=%s actual=%sx%s@%s",
                    self._config.camera_id,
                    self._actual_width,
                    self._actual_height,
                    self._actual_fps,
                )
            except CameraError as exc:
                self._release_capture()
                self._state = CameraState.ERROR
                self._error = exc.message
                raise
            except Exception as exc:
                self._release_capture()
                self._state = CameraState.ERROR
                self._error = "Failed to open camera"
                logger.exception("Unexpected error opening camera %s", self._config.camera_id)
                raise CameraOpenError("Failed to open camera") from exc

    def start(self) -> None:
        with self._lock:
            if self._state == CameraState.RUNNING:
                raise CameraAlreadyRunningError(self._config.camera_id)
            if self._state not in {CameraState.OPEN, CameraState.STOPPED}:
                raise CameraInvalidStateError(
                    f"Camera '{self._config.camera_id}' must be open before start"
                )
            self._stop_event.clear()
            self._frames.clear()
            thread = threading.Thread(
                target=self._capture_loop,
                name=f"camera-{self._config.camera_id}",
                daemon=False,
            )
            self._thread = thread
            self._state = CameraState.RUNNING
        thread.start()
        logger.info("Camera started id=%s", self._config.camera_id)

    def read(self) -> Frame | None:
        with self._lock:
            if self._state == CameraState.ERROR:
                raise CameraReadError(self._error or "Camera read failed")
            if self._state != CameraState.RUNNING:
                raise CameraInvalidStateError(f"Camera '{self._config.camera_id}' is not running")
        return self._frames.get()

    def stop(self) -> None:
        with self._lock:
            if self._state != CameraState.RUNNING:
                raise CameraInvalidStateError(f"Camera '{self._config.camera_id}' is not running")
            self._stop_event.set()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=_THREAD_JOIN_TIMEOUT_SECONDS)
            if thread.is_alive():
                logger.error("Camera thread did not stop in time id=%s", self._config.camera_id)
        with self._lock:
            self._thread = None
            if self._state == CameraState.RUNNING:
                self._state = CameraState.STOPPED
            logger.info("Camera stopped id=%s", self._config.camera_id)

    def close(self) -> None:
        with self._lock:
            if self._state == CameraState.CLOSED:
                return
            running = self._state == CameraState.RUNNING
            self._stop_event.set()
            thread = self._thread
        if running and thread is not None:
            thread.join(timeout=_THREAD_JOIN_TIMEOUT_SECONDS)
            if thread.is_alive():
                logger.error(
                    "Camera thread did not stop during close id=%s", self._config.camera_id
                )
        with self._lock:
            self._thread = None
            self._release_capture()
            self._frames.clear()
            self._state = CameraState.CLOSED
            logger.info("Camera closed id=%s", self._config.camera_id)

    def is_open(self) -> bool:
        return self._state in {CameraState.OPEN, CameraState.RUNNING, CameraState.STOPPED}

    def is_running(self) -> bool:
        return self._state == CameraState.RUNNING

    def get_status(self) -> CameraStatus:
        with self._lock:
            return CameraStatus(
                id=self._config.camera_id,
                name=self._config.name,
                state=self._state,
                device_index=self._config.device_index,
                width=self._actual_width,
                height=self._actual_height,
                fps=self._actual_fps,
                last_frame_at=self._last_frame_at,
                error=self._error,
            )

    def _open_device(self) -> VideoCaptureLike:
        last_error: str | None = None
        for api in _fallback_preferences(self._config.backend):
            capture = self._opener(self._config.device_index, api)
            if capture.isOpened():
                return capture
            capture.release()
            last_error = f"device index {self._config.device_index} did not open"
        raise CameraNotAvailableError(
            last_error or f"USB camera index {self._config.device_index} is not available"
        )

    def _configure_capture(self, capture: VideoCaptureLike) -> None:
        import cv2

        requested = {
            "width": (cv2.CAP_PROP_FRAME_WIDTH, float(self._config.width)),
            "height": (cv2.CAP_PROP_FRAME_HEIGHT, float(self._config.height)),
            "fps": (cv2.CAP_PROP_FPS, float(self._config.fps)),
        }
        buffer_prop = getattr(cv2, "CAP_PROP_BUFFERSIZE", None)
        if isinstance(buffer_prop, int):
            capture.set(buffer_prop, 1.0)
        for name, (prop, value) in requested.items():
            applied = capture.set(prop, value)
            actual = capture.get(prop)
            if not applied:
                logger.warning(
                    "Camera id=%s rejected %s=%s (driver returned false)",
                    self._config.camera_id,
                    name,
                    value,
                )
            elif abs(actual - value) > 1.0:
                logger.warning(
                    "Camera id=%s %s requested=%s actual=%s",
                    self._config.camera_id,
                    name,
                    value,
                    actual,
                )
        self._actual_width = max(int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), 1)
        self._actual_height = max(int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)), 1)
        actual_fps = float(capture.get(cv2.CAP_PROP_FPS))
        self._actual_fps = actual_fps if actual_fps > 0 else self._config.fps

    def _verify_capture(self, capture: VideoCaptureLike) -> None:
        ok, image = capture.read()
        if not ok or image is None:
            raise CameraOpenError(
                f"USB camera index {self._config.device_index} opened but did not return a frame"
            )
        self._store_frame(image)

    def _store_frame(self, image: NDArray[np.uint8]) -> None:
        copied = np.ascontiguousarray(image.copy())
        height, width = copied.shape[0], copied.shape[1]
        timestamp = datetime.now(UTC)
        with self._lock:
            self._actual_height = int(height)
            self._actual_width = int(width)
            self._last_frame_at = timestamp
        self._frames.put(
            Frame(data=copied, timestamp=timestamp, width=int(width), height=int(height))
        )

    def _capture_loop(self) -> None:
        failures = 0
        while not self._stop_event.is_set():
            capture = self._capture
            if capture is None:
                break
            try:
                ok, image = capture.read()
            except Exception:
                logger.exception("Camera read raised id=%s", self._config.camera_id)
                ok, image = False, None
            if not ok or image is None:
                failures += 1
                if failures >= _MAX_CONSECUTIVE_READ_FAILURES:
                    message = "Camera stopped returning frames"
                    logger.error("Camera read failed id=%s", self._config.camera_id)
                    with self._lock:
                        self._state = CameraState.ERROR
                        self._error = message
                    break
                time.sleep(0.05)
                continue
            failures = 0
            self._store_frame(image)
        logger.info("Capture loop exiting id=%s", self._config.camera_id)

    def _release_capture(self) -> None:
        capture = self._capture
        self._capture = None
        if capture is not None:
            try:
                capture.release()
            except Exception:
                logger.exception("Error releasing camera id=%s", self._config.camera_id)
