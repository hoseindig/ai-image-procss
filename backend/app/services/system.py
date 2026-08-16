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
    ReadyCheck,
    ReadyResponse,
    SystemStatusResponse,
)
from app.vision.runtime import DetectionRuntime

logger = get_logger("app")


class HealthService:
    def get_health(self) -> HealthResponse:
        return HealthResponse(status="ok")


class ReadyService:
    """Readiness: DB + models when features are enabled. Camera is not required."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_ready(self, session: Session, detection_runtime: DetectionRuntime) -> ReadyResponse:
        db_ok = self._database_connected(session)
        models_ok, models_detail = self._models_ready(detection_runtime)
        ready = db_ok and models_ok
        return ReadyResponse(
            status="ready" if ready else "not_ready",
            database=ReadyCheck(ok=db_ok, detail=None if db_ok else "database_unavailable"),
            models=ReadyCheck(ok=models_ok, detail=models_detail),
        )

    def _database_connected(self, session: Session) -> bool:
        try:
            session.scalar(select(literal(1)))
            return True
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Database connectivity check failed")
            return False

    def _models_ready(self, detection_runtime: DetectionRuntime) -> tuple[bool, str | None]:
        if self._settings.face_detection_enabled and not detection_runtime.model_loaded:
            return False, "face_detection_model_not_loaded"
        if self._settings.face_embedding_enabled and not detection_runtime.embedding_enabled:
            return False, "face_embedding_model_not_loaded"
        return True, None


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
        ready_body = ReadyService(self._settings).get_ready(session, detection_runtime)
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
                embedding_enabled=detection_runtime.embedding_enabled,
                embedding_provider=detection_runtime.embedding_provider,
                recognition_enabled=detection_runtime.recognition_enabled,
                recognition_threshold=detection_runtime.recognition_threshold,
                event_logging_enabled=detection_runtime.event_logging_enabled,
            ),
            ready=ready_body.status == "ready",
        )

    def _database_connected(self, session: Session) -> bool:
        try:
            session.scalar(select(literal(1)))
            return True
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Database connectivity check failed")
            return False
