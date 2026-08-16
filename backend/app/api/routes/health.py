"""Health and system status routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import (
    CameraManagerDep,
    DetectionRuntimeDep,
    SessionDep,
    SettingsDep,
    StartedAtDep,
)
from app.schemas.health import HealthResponse, SystemStatusResponse
from app.services.system import HealthService, SystemStatusService

router = APIRouter(tags=["system"])


@router.get("/health")
def get_health() -> HealthResponse:
    return HealthService().get_health()


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
