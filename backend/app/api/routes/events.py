"""Event list/detail routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.events.types import EventType
from app.schemas.event import EventListResponse, EventResponse
from app.services.event import EventListResult, EventRecord, EventService

router = APIRouter(prefix="/events", tags=["events"])


def get_event_service(request: Request) -> EventService:
    service = getattr(request.app.state, "event_service", None)
    if not isinstance(service, EventService):
        raise RuntimeError("Event service is not initialized")
    return service


EventServiceDep = Annotated[EventService, Depends(get_event_service)]


def _to_response(record: EventRecord) -> EventResponse:
    return EventResponse(
        id=record.id,
        event_type=record.event_type,
        camera_id=record.camera_id,
        track_id=record.track_id,
        person_id=record.person_id,
        enrollment_id=record.enrollment_id,
        similarity=record.similarity,
        occurred_at=record.occurred_at,
        created_at=record.created_at,
    )


@router.get("")
def list_events(
    service: EventServiceDep,
    camera_id: str | None = None,
    person_id: str | None = None,
    event_type: EventType | None = None,
    occurred_from: Annotated[
        datetime | None,
        Query(alias="from", description="Inclusive UTC lower bound on occurred_at"),
    ] = None,
    occurred_to: Annotated[
        datetime | None,
        Query(alias="to", description="Inclusive UTC upper bound on occurred_at"),
    ] = None,
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1),
) -> EventListResponse:
    result: EventListResult = service.list_events(
        camera_id=camera_id,
        person_id=person_id,
        event_type=event_type,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        page=page,
        page_size=page_size,
    )
    return EventListResponse(
        items=[_to_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.get("/{event_id}")
def get_event(event_id: str, service: EventServiceDep) -> EventResponse:
    return _to_response(service.get_event(event_id))
