from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadyCheck(BaseModel):
    ok: bool
    detail: str | None = None


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: ReadyCheck
    models: ReadyCheck
    # Camera is operational state, not a readiness gate for the process.
    camera_required_for_ready: Literal[False] = False


class DatabaseStatus(BaseModel):
    connected: bool


class CameraHealthStatus(BaseModel):
    available: bool
    running: bool


class FaceDetectionHealthStatus(BaseModel):
    enabled: bool
    model_loaded: bool
    provider: str | None = None
    last_inference_ms: float | None = None
    tracking_enabled: bool
    quality_enabled: bool = False
    alignment_enabled: bool = False
    embedding_enabled: bool = False
    embedding_provider: str | None = None
    recognition_enabled: bool = False
    recognition_threshold: float | None = None
    event_logging_enabled: bool = False


class SystemStatusResponse(BaseModel):
    status: Literal["ok", "degraded"]
    environment: str
    python_version: str
    uptime_seconds: float = Field(ge=0)
    database: DatabaseStatus
    camera: CameraHealthStatus
    face_detection: FaceDetectionHealthStatus
    ready: bool = False
