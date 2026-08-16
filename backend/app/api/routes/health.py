"""Health and system status routes."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import (
    CameraManagerDep,
    DetectionRuntimeDep,
    SessionDep,
    SettingsDep,
    StartedAtDep,
)
from app.schemas.health import HealthResponse, ReadyResponse, SystemStatusResponse
from app.services.system import HealthService, ReadyService, SystemStatusService

router = APIRouter(tags=["system"])


@router.get("/health")
def get_health() -> HealthResponse:
    """Liveness: process is up. Does not require database, models, or camera."""
    return HealthService().get_health()


@router.get("/ready")
def get_ready(
    settings: SettingsDep,
    session: SessionDep,
    detection_runtime: DetectionRuntimeDep,
    response: Response,
) -> ReadyResponse:
    """Readiness: database reachable and required models loaded when features enabled."""
    body = ReadyService(settings).get_ready(session, detection_runtime)
    if body.status != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return body


@router.get("/system/status")
def get_system_status(
    settings: SettingsDep,
    started_at: StartedAtDep,
    session: SessionDep,
    camera_manager: CameraManagerDep,
    detection_runtime: DetectionRuntimeDep,
) -> SystemStatusResponse:
    return SystemStatusService(settings, started_at).get_status(
        session, camera_manager, detection_runtime
    )
