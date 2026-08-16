from __future__ import annotations

from pydantic import BaseModel

from app.cameras.types import CameraStatus


class CameraListResponse(BaseModel):
    cameras: list[CameraStatus]
