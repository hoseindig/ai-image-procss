"""Latest-value slot. Capacity is always 1; a new put drops the previous value."""

from __future__ import annotations

import threading


class LatestValueSlot[T]:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._value: T | None = None

    def put(self, value: T) -> None:
        with self._lock:
            self._value = value

    def get(self) -> T | None:
        with self._lock:
            return self._value

    def clear(self) -> None:
        with self._lock:
            self._value = None
