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


def create_app(
    settings: Settings | None = None,
    camera_manager: CameraManager | None = None,
) -> FastAPI:
    """Build the FastAPI application.

    Tests pass an explicit Settings instance. Production uses `load_settings()`.
    """
    resolved = settings or load_settings()
    setup_logging(resolved.log_level)
    logger = get_logger("app")
    manager = camera_manager
    if manager is None:
        manager = CameraManager()
        manager.register(config_from_settings(resolved))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved
        app.state.started_at = datetime.now(UTC)
        app.state.database = Database(resolved.database_url)
        app.state.camera_manager = manager
        logger.info("Application started (%s)", resolved.app_env)
        try:
            yield
        finally:
            manager.shutdown()
            database = getattr(app.state, "database", None)
            if isinstance(database, Database):
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
