"""Person and enrollment routes. Thin handlers; logic lives in services."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import CameraManagerDep, DetectionRuntimeDep, SessionDep, SettingsDep
from app.persons.enrollment_session import EnrollmentSessionStore
from app.schemas.enrollment_session import EnrollmentSessionCreateRequest, EnrollmentSessionResponse
from app.schemas.person import (
    EnrollmentCreateRequest,
    EnrollmentListResponse,
    EnrollmentResponse,
    PersonCreateRequest,
    PersonListResponse,
    PersonResponse,
    PersonUpdateRequest,
)
from app.services.enrollment import EnrollmentService
from app.services.enrollment_session import EnrollmentSessionService
from app.services.person import PersonService

router = APIRouter(prefix="/persons", tags=["persons"])


def get_person_service(session: SessionDep) -> PersonService:
    return PersonService(session)


def get_enrollment_service(session: SessionDep) -> EnrollmentService:
    return EnrollmentService(session)


def get_enrollment_session_store(request: Request) -> EnrollmentSessionStore:
    store = getattr(request.app.state, "enrollment_session_store", None)
    if not isinstance(store, EnrollmentSessionStore):
        raise RuntimeError("Enrollment session store is not initialized")
    return store


def get_enrollment_session_service(
    request: Request,
    session: SessionDep,
    manager: CameraManagerDep,
    runtime: DetectionRuntimeDep,
    settings: SettingsDep,
) -> EnrollmentSessionService:
    store = get_enrollment_session_store(request)
    return EnrollmentSessionService(
        store,
        PersonService(session),
        EnrollmentService(session),
        manager,
        runtime,
        default_camera_id=settings.camera_default_id,
    )


PersonServiceDep = Annotated[PersonService, Depends(get_person_service)]
EnrollmentServiceDep = Annotated[EnrollmentService, Depends(get_enrollment_service)]
EnrollmentSessionServiceDep = Annotated[
    EnrollmentSessionService, Depends(get_enrollment_session_service)
]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_person(body: PersonCreateRequest, service: PersonServiceDep) -> PersonResponse:
    return service.create_person(body.display_name)


@router.get("")
def list_persons(service: PersonServiceDep) -> PersonListResponse:
    return PersonListResponse(persons=service.list_persons())


@router.get("/{person_id}")
def get_person(person_id: str, service: PersonServiceDep) -> PersonResponse:
    return service.get_person(person_id)


@router.patch("/{person_id}")
def update_person(
    person_id: str,
    body: PersonUpdateRequest,
    service: PersonServiceDep,
) -> PersonResponse:
    return service.update_person(
        person_id,
        display_name=body.display_name,
        active=body.active,
    )


@router.delete("/{person_id}", status_code=status.HTTP_200_OK)
def deactivate_person(person_id: str, service: PersonServiceDep) -> PersonResponse:
    """Soft-deactivate a person. Does not hard-delete history or enrollments."""
    return service.deactivate_person(person_id)


@router.post("/{person_id}/enrollments", status_code=status.HTTP_201_CREATED)
def create_enrollment(
    person_id: str,
    body: EnrollmentCreateRequest,
    service: EnrollmentServiceDep,
) -> EnrollmentResponse:
    """Developer/testing: accept a precomputed embedding. Prefer enrollment-sessions."""
    return service.add_embedding(
        person_id,
        body.embedding,
        quality_accepted=body.quality.accepted,
        normalized=body.normalized,
        face_width=body.quality.face_width,
        face_height=body.quality.face_height,
        sharpness=body.quality.sharpness,
        brightness=body.quality.brightness,
        source_track_id=body.source_track_id,
    )


@router.get("/{person_id}/enrollments")
def list_enrollments(person_id: str, service: EnrollmentServiceDep) -> EnrollmentListResponse:
    return EnrollmentListResponse(enrollments=service.list_enrollments(person_id))


@router.delete(
    "/{person_id}/enrollments/{enrollment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_enrollment(
    person_id: str,
    enrollment_id: str,
    service: EnrollmentServiceDep,
) -> Response:
    service.delete_enrollment(person_id, enrollment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{person_id}/enrollment-sessions",
    status_code=status.HTTP_201_CREATED,
    tags=["enrollment-sessions"],
)
def start_enrollment_session(
    person_id: str,
    service: EnrollmentSessionServiceDep,
    body: EnrollmentSessionCreateRequest | None = None,
) -> EnrollmentSessionResponse:
    payload = body or EnrollmentSessionCreateRequest()
    return service.start_session(person_id, camera_id=payload.camera_id)


@router.get(
    "/{person_id}/enrollment-sessions/{session_id}",
    tags=["enrollment-sessions"],
)
def get_enrollment_session(
    person_id: str,
    session_id: str,
    service: EnrollmentSessionServiceDep,
) -> EnrollmentSessionResponse:
    return service.get_session(person_id, session_id)


@router.post(
    "/{person_id}/enrollment-sessions/{session_id}/capture",
    tags=["enrollment-sessions"],
)
def capture_enrollment_session(
    person_id: str,
    session_id: str,
    service: EnrollmentSessionServiceDep,
) -> EnrollmentSessionResponse:
    return service.capture(person_id, session_id)


@router.delete(
    "/{person_id}/enrollment-sessions/{session_id}",
    tags=["enrollment-sessions"],
)
def cancel_enrollment_session(
    person_id: str,
    session_id: str,
    service: EnrollmentSessionServiceDep,
) -> EnrollmentSessionResponse:
    return service.cancel(person_id, session_id)
