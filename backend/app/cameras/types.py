"""Camera domain types. No OpenCV types leak through this module."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field


class SourceType(StrEnum):
    USB = "usb"
    RTSP = "rtsp"
    FILE = "file"
    HTTP = "http"


class CameraState(StrEnum):
    CLOSED = "closed"
    OPENING = "opening"
    OPEN = "open"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class CameraConfig(BaseModel):
    camera_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    source_type: SourceType = SourceType.USB
    device_index: int = Field(default=0, ge=0)
    enabled: bool = True
    width: int = Field(default=1280, ge=1)
    height: int = Field(default=720, ge=1)
    fps: float = Field(default=15.0, gt=0)
    backend: str = Field(default="dshow")
    # Consecutive failed VideoCapture.read() calls before ERROR (USB capture thread).
    max_consecutive_read_failures: int = Field(default=30, ge=1, le=1000)


class CameraStatus(BaseModel):
    id: str
    name: str
    state: CameraState
    device_index: int
    width: int
    height: int
    fps: float
    last_frame_at: datetime | None = None
    error: str | None = None


class Frame:
    """One captured image plus metadata.

    `data` is an H×W×3 uint8 array in BGR order (USB capture convention).
    Callers must not assume an OpenCV type; it is a NumPy array.
    """

    __slots__ = ("data", "height", "timestamp", "width")

    def __init__(
        self,
        data: NDArray[np.uint8],
        timestamp: datetime,
        width: int,
        height: int,
    ) -> None:
        self.data = data
        self.timestamp = timestamp
        self.width = width
        self.height = height
