"""Event repository. Application code uses EventService, not this table directly."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import Session

from app.events.types import EventType
from app.models.event import Event


class EventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: Event) -> Event:
        self._session.add(event)
        self._session.commit()
        self._session.refresh(event)
        return event

    def get(self, event_id: str) -> Event | None:
        return self._session.get(Event, event_id)

    def delete_older_than(self, cutoff: datetime) -> int:
        """Delete events with occurred_at strictly before cutoff. Returns row count."""
        from sqlalchemy import CursorResult, delete

        result = self._session.execute(delete(Event).where(Event.occurred_at < cutoff))
        self._session.commit()
        if isinstance(result, CursorResult):
            return int(result.rowcount or 0)
        return 0

    def list_events(
        self,
        *,
        camera_id: str | None = None,
        person_id: str | None = None,
        event_type: EventType | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Event], int]:
        filters = _filters(
            camera_id=camera_id,
            person_id=person_id,
            event_type=event_type,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )
        count_stmt = select(func.count()).select_from(Event)
        list_stmt: Select[tuple[Event]] = select(Event)
        for clause in filters:
            count_stmt = count_stmt.where(clause)
            list_stmt = list_stmt.where(clause)
        total = int(self._session.scalar(count_stmt) or 0)
        rows = self._session.scalars(
            list_stmt.order_by(Event.occurred_at.desc(), Event.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return list(rows), total


def _filters(
    *,
    camera_id: str | None,
    person_id: str | None,
    event_type: EventType | None,
    occurred_from: datetime | None,
    occurred_to: datetime | None,
) -> list[ColumnElement[bool]]:
    clauses: list[ColumnElement[bool]] = []
    if camera_id is not None:
        clauses.append(Event.camera_id == camera_id)
    if person_id is not None:
        clauses.append(Event.person_id == person_id)
    if event_type is not None:
        clauses.append(Event.event_type == event_type.value)
    if occurred_from is not None:
        clauses.append(Event.occurred_at >= occurred_from)
    if occurred_to is not None:
        clauses.append(Event.occurred_at <= occurred_to)
    return clauses
