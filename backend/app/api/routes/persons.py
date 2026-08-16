"""Person and enrollment routes. Thin handlers; logic lives in services."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import SessionDep
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
from app.services.person import PersonService

router = APIRouter(prefix="/persons", tags=["persons"])


def get_person_service(session: SessionDep) -> PersonService:
    return PersonService(session)


def get_enrollment_service(session: SessionDep) -> EnrollmentService:
    return EnrollmentService(session)


PersonServiceDep = Annotated[PersonService, Depends(get_person_service)]
EnrollmentServiceDep = Annotated[EnrollmentService, Depends(get_enrollment_service)]


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
