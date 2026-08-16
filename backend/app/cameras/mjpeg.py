"""MJPEG encoding helpers. OpenCV is confined to this module."""

from __future__ import annotations

import time
from collections.abc import Iterator

import numpy as np
from numpy.typing import NDArray

from app.cameras.source import CameraSource
from app.cameras.types import Frame
from app.core.logging import get_logger

logger = get_logger("app.camera")

BOUNDARY = b"frame"
CONTENT_TYPE = f"multipart/x-mixed-replace; boundary={BOUNDARY.decode()}"


def encode_jpeg(frame_bgr: NDArray[np.uint8], *, quality: int = 80) -> bytes:
    """Encode a BGR uint8 image to JPEG bytes."""
    import cv2

    quality = max(1, min(100, quality))
    ok, encoded = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("Failed to encode JPEG frame")
    return encoded.tobytes()


def frame_to_multipart(frame: Frame, *, quality: int = 80) -> bytes:
    jpeg = encode_jpeg(frame.data, quality=quality)
    header = (
        b"--"
        + BOUNDARY
        + b"\r\nContent-Type: image/jpeg\r\nContent-Length: "
        + str(len(jpeg)).encode("ascii")
        + b"\r\n\r\n"
    )
    return header + jpeg + b"\r\n"


def iter_mjpeg(
    source: CameraSource,
    *,
    fps: float = 10.0,
    quality: int = 80,
    idle_sleep_seconds: float = 0.05,
    max_frames: int | None = None,
) -> Iterator[bytes]:
    """Yield multipart MJPEG chunks from a running camera source.

    Drops frames when the client is slow; uses the latest-frame slot via ``read()``.
    Stops when the client disconnects (``GeneratorExit``) or ``max_frames`` is reached.
    """
    interval = 1.0 / max(fps, 0.1)
    emitted = 0
    try:
        while max_frames is None or emitted < max_frames:
            started = time.perf_counter()
            try:
                frame = source.read()
            except Exception:
                logger.exception("MJPEG preview read failed")
                break
            if frame is None:
                time.sleep(idle_sleep_seconds)
                continue
            yield frame_to_multipart(frame, quality=quality)
            emitted += 1
            elapsed = time.perf_counter() - started
            remaining = interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
    except GeneratorExit:
        return
