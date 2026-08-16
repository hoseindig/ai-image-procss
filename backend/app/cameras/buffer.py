"""Bounded latest-frame slot. Capacity is always 1; a new put drops the previous frame."""

from __future__ import annotations

import threading

from app.cameras.types import Frame


class LatestFrameSlot:
    """Single-slot buffer. Never grows; stale frames are replaced, not queued."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frame: Frame | None = None

    def put(self, frame: Frame) -> None:
        with self._lock:
            self._frame = frame

    def get(self) -> Frame | None:
        with self._lock:
            return self._frame

    def clear(self) -> None:
        with self._lock:
            self._frame = None
