"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.cameras.manager import CameraManager, config_from_settings
from app.core.config import Settings, load_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.db.session import Database
from app.persons.enrollment_session import EnrollmentSessionStore
from app.services.event import EventService, EventServiceConfig
from app.vision.detector import FaceDetector
from app.vision.factory import (
    create_event_service,
    create_face_detector,
    create_face_embedder,
    create_face_recognizer,
)
from app.vision.runtime import DetectionRuntime


def create_app(
    settings: Settings | None = None,
    camera_manager: CameraManager | None = None,
    face_detector: FaceDetector | None = None,
    enrollment_session_store: EnrollmentSessionStore | None = None,
) -> FastAPI:
    """Build the FastAPI application.

    Tests pass an explicit Settings instance. Production uses `load_settings()`.
    Pass `face_detector` to inject a fake detector; otherwise YuNet is loaded
    during lifespan when face detection is enabled.
    """
    resolved = settings or load_settings()
    setup_logging(resolved.log_level)
    logger = get_logger("app")
    manager = camera_manager
    if manager is None:
        manager = CameraManager()
        manager.register(config_from_settings(resolved))
    session_store = enrollment_session_store or EnrollmentSessionStore()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        detector = face_detector
        if detector is None and resolved.face_detection_enabled:
            detector = create_face_detector(resolved)
        database = Database(resolved.database_url)
        embedder = create_face_embedder(resolved)
        recognizer = create_face_recognizer(resolved, database)
        event_service = create_event_service(resolved, database)
        runtime = DetectionRuntime(
            detector,
            resolved,
            manager,
            embedder=embedder,
            recognizer=recognizer,
            event_service=event_service,
        )
        app.state.settings = resolved
        app.state.started_at = datetime.now(UTC)
        app.state.database = database
        app.state.camera_manager = manager
        app.state.detection_runtime = runtime
        app.state.enrollment_session_store = session_store
        app.state.event_service = event_service or EventService(
            database,
            EventServiceConfig(enabled=False),
        )
        logger.info("Application started (%s)", resolved.app_env)
        try:
            yield
        finally:
            runtime.shutdown()
            manager.shutdown()
            database.dispose()
            logger.info("Application stopped")

    application = FastAPI(
        title=resolved.app_name,
        # Keep Starlette debug tracebacks off the HTTP response. `settings.debug`
        # only controls whether a short exception message is included in JSON.
        debug=False,
        lifespan=lifespan,
    )
    application.state.settings = resolved
    application.state.enrollment_session_store = session_store
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    register_exception_handlers(application, resolved)
    application.include_router(api_router, prefix="/api")
    return application


app = create_app()
