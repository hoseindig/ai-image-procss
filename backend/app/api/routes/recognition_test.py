"""TEST ONLY recognition endpoint — gated by RECOGNITION_TEST_MODE.

POST /api/test/recognize
  multipart file: pre-aligned 112×112 PNG/JPEG (BGR crop after decode)

Disabled by default. Does not change the webcam pipeline.
Does not return embeddings.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.core.config import Settings
from app.schemas.recognition_test import RecognitionTestResponse
from app.services.event import EventService
from app.services.recognition_test import (
    RecognitionTestDisabledError,
    RecognitionTestInputError,
    RecognitionTestService,
)
from app.vision.runtime import DetectionRuntime

router = APIRouter(prefix="/test", tags=["test-only"])


def get_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("Settings are not initialized")
    return settings


def get_runtime(request: Request) -> DetectionRuntime:
    runtime = getattr(request.app.state, "detection_runtime", None)
    if not isinstance(runtime, DetectionRuntime):
        raise RuntimeError("Detection runtime is not initialized")
    return runtime


def get_event_service(request: Request) -> EventService:
    service = getattr(request.app.state, "event_service", None)
    if not isinstance(service, EventService):
        raise RuntimeError("Event service is not initialized")
    return service


def get_recognition_test_service(
    settings: Annotated[Settings, Depends(get_settings)],
    runtime: Annotated[DetectionRuntime, Depends(get_runtime)],
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> RecognitionTestService:
    if not settings.recognition_test_mode:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "recognition_test_disabled",
                    "message": (
                        "Recognition test mode is disabled "
                        "(set RECOGNITION_TEST_MODE=true only for local tests)"
                    ),
                }
            },
        )

    embedder = runtime.embedder
    recognizer = runtime.recognizer
    if embedder is None or recognizer is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "recognition_test_unavailable",
                    "message": (
                        "TEST ONLY recognition requires face embedding and "
                        "recognition to be enabled with models loaded"
                    ),
                }
            },
        )
    return RecognitionTestService(
        enabled=True,
        embedder=embedder,
        recognizer=recognizer,
        event_service=event_service,
        recognition_threshold=settings.face_recognition_threshold,
    )


RecognitionTestServiceDep = Annotated[RecognitionTestService, Depends(get_recognition_test_service)]


@router.post(
    "/recognize",
    response_model=RecognitionTestResponse,
    summary="TEST ONLY — recognize a pre-aligned 112×112 face crop",
)
async def recognize_test_image(
    service: RecognitionTestServiceDep,
    file: Annotated[UploadFile, File(description="TEST ONLY: aligned 112×112 PNG/JPEG")],
    camera_id: Annotated[str, Form()] = "test",
    track_id: Annotated[int, Form()] = 1,
    record_event: Annotated[bool, Form()] = True,
) -> RecognitionTestResponse:
    """TEST ONLY. Requires RECOGNITION_TEST_MODE=true. Webcam path unchanged."""
    try:
        service.require_enabled()
    except RecognitionTestDisabledError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "recognition_test_disabled",
                    "message": str(exc),
                }
            },
        ) from exc

    data = await file.read()
    try:
        outcome = service.recognize_image_bytes(
            data,
            camera_id=camera_id,
            track_id=track_id,
            record_event=record_event,
        )
    except RecognitionTestInputError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "recognition_test_invalid_input",
                    "message": str(exc),
                }
            },
        ) from exc

    return RecognitionTestResponse(
        test_only=True,
        status=outcome.status,
        track_id=outcome.track_id,
        person_id=outcome.person_id,
        person_display_name=outcome.person_display_name,
        similarity=outcome.similarity,
        enrollment_id=outcome.enrollment_id,
        reason=outcome.reason,
        event_id=outcome.event_id,
        event_created=outcome.event_created,
        camera_id=outcome.camera_id,
        threshold=outcome.threshold,
    )
