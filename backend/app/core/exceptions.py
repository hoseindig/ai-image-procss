"""Centralized FastAPI exception handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.cameras.exceptions import CameraError
from app.cameras.http import camera_error_http_status
from app.core.config import Settings
from app.core.logging import get_logger
from app.vision.exceptions import VisionError
from app.vision.http import vision_error_http_status

logger = get_logger("app")


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    """Register process-wide exception handlers. Validation errors stay default."""

    @app.exception_handler(CameraError)
    async def camera_exception_handler(_request: Request, exc: CameraError) -> JSONResponse:
        logger.warning("Camera error: %s", exc.message)
        return JSONResponse(
            status_code=camera_error_http_status(exc),
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(VisionError)
    async def vision_exception_handler(_request: Request, exc: VisionError) -> JSONResponse:
        logger.warning("Vision error: %s", exc.message)
        return JSONResponse(
            status_code=vision_error_http_status(exc),
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled error on %s %s",
            request.method,
            request.url.path,
        )
        payload: dict[str, dict[str, str]] = {
            "error": {
                "code": "internal_error",
                "message": "Internal server error",
            }
        }
        if settings.debug:
            payload["error"]["details"] = str(exc)
        return JSONResponse(status_code=500, content=payload)
