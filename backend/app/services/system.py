"""System health and status services."""

from __future__ import annotations

import sys
from datetime import UTC, datetime

from sqlalchemy import literal, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.cameras.manager import CameraManager
from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.health import (
    CameraHealthStatus,
    DatabaseStatus,
    FaceDetectionHealthStatus,
    HealthResponse,
    SystemStatusResponse,
)
from app.vision.runtime import DetectionRuntime

logger = get_logger("app")


class HealthService:
    def get_health(self) -> HealthResponse:
        return HealthResponse(status="ok")


class SystemStatusService:
    def __init__(self, settings: Settings, started_at: datetime) -> None:
        self._settings = settings
        self._started_at = started_at

    def get_status(
        self,
        session: Session,
        camera_manager: CameraManager,
        detection_runtime: DetectionRuntime,
    ) -> SystemStatusResponse:
        connected = self._database_connected(session)
        available, running = camera_manager.summary()
        uptime = max((datetime.now(UTC) - self._started_at).total_seconds(), 0.0)
        return SystemStatusResponse(
            status="ok" if connected else "degraded",
            environment=self._settings.app_env,
            python_version=sys.version.split()[0],
            uptime_seconds=round(uptime, 3),
            database=DatabaseStatus(connected=connected),
            camera=CameraHealthStatus(available=available, running=running),
            face_detection=FaceDetectionHealthStatus(
                enabled=detection_runtime.enabled,
                model_loaded=detection_runtime.model_loaded,
                provider=detection_runtime.provider,
                last_inference_ms=detection_runtime.last_inference_ms(),
                tracking_enabled=detection_runtime.tracking_enabled,
                quality_enabled=detection_runtime.quality_enabled,
                alignment_enabled=detection_runtime.alignment_enabled,
            ),
        )

    def _database_connected(self, session: Session) -> bool:
        try:
            session.scalar(select(literal(1)))
            return True
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Database connectivity check failed")
            return False
