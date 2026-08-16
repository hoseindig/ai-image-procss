from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]


class DatabaseStatus(BaseModel):
    connected: bool


class CameraHealthStatus(BaseModel):
    available: bool
    running: bool


class SystemStatusResponse(BaseModel):
    status: Literal["ok", "degraded"]
    environment: str
    python_version: str
    uptime_seconds: float = Field(ge=0)
    database: DatabaseStatus
    camera: CameraHealthStatus
