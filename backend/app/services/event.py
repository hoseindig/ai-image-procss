"""EventService: cooldown deduplication + persistence after recognition."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.logging import get_logger
from app.db.session import Database
from app.events.exceptions import EventNotFoundError, EventValidationError
from app.events.repository import EventRepository
from app.events.types import EventType
from app.models.event import Event
from app.vision.recognizer import RecognitionResult
from app.vision.types import RecognitionStatus

logger = get_logger("app.events")


@dataclass(frozen=True)
class EventRecord:
    """API/service DTO. No embeddings or images."""

    id: str
    event_type: EventType
    camera_id: str
    track_id: int
    person_id: str | None
    enrollment_id: str | None
    similarity: float | None
    occurred_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class EventListResult:
    items: list[EventRecord]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True)
class EventServiceConfig:
    enabled: bool = True
    recognized_cooldown_seconds: float = 10.0
    unknown_cooldown_seconds: float = 10.0
    default_page_size: int = 50
    max_page_size: int = 200
    retention_days: int = 90
    retention_enabled: bool = True


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _to_record(row: Event) -> EventRecord:
    return EventRecord(
        id=row.id,
        event_type=EventType(row.event_type),
        camera_id=row.camera_id,
        track_id=row.track_id,
        person_id=row.person_id,
        enrollment_id=row.enrollment_id,
        similarity=row.similarity,
        occurred_at=row.occurred_at,
        created_at=row.created_at,
    )


class EventService:
    """Records recognized/unknown_face events with in-memory cooldown keys.

    Recognized cooldown key: (camera_id, person_id) — Track ID is not durable identity.
    Unknown cooldown key: (camera_id, track_id) — process-local only.
    """

    def __init__(self, database: Database, config: EventServiceConfig) -> None:
        self._database = database
        self._config = config
        self._lock = threading.Lock()
        # key -> monotonic timestamp of last emitted event
        self._last_emit: dict[tuple[str, ...], float] = {}

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def config(self) -> EventServiceConfig:
        return self._config

    def record_from_recognition(
        self,
        camera_id: str,
        result: RecognitionResult,
        *,
        occurred_at: datetime | None = None,
    ) -> EventRecord | None:
        """Persist a recognition event when cooldown allows. Never raises to callers.

        Recognition remains valid even if persistence fails (logged).
        """
        if not self._config.enabled:
            return None
        if result.status is RecognitionStatus.MATCHED:
            event_type = EventType.RECOGNIZED
            if result.person_id is None:
                logger.warning(
                    "Skipping recognized event without person_id camera_id=%s track_id=%s",
                    camera_id,
                    result.track_id,
                )
                return None
            cooldown_key: tuple[str, ...] = ("recognized", camera_id, result.person_id)
            cooldown_s = self._config.recognized_cooldown_seconds
        elif result.status is RecognitionStatus.UNKNOWN:
            event_type = EventType.UNKNOWN_FACE
            cooldown_key = ("unknown", camera_id, str(result.track_id))
            cooldown_s = self._config.unknown_cooldown_seconds
        else:
            return None

        now_mono = time.monotonic()
        with self._lock:
            last = self._last_emit.get(cooldown_key)
            if last is not None and (now_mono - last) < cooldown_s:
                return None
            # Reserve the slot before DB write to avoid stampedes; roll back on failure.
            self._last_emit[cooldown_key] = now_mono

        when = occurred_at or _utc_now()
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        created = _utc_now()
        event = Event(
            id=str(uuid4()),
            event_type=event_type.value,
            camera_id=camera_id,
            track_id=result.track_id,
            person_id=result.person_id if event_type is EventType.RECOGNIZED else None,
            enrollment_id=(result.enrollment_id if event_type is EventType.RECOGNIZED else None),
            similarity=result.similarity,
            occurred_at=when,
            created_at=created,
        )
        try:
            with self._database.session() as session:
                saved = EventRepository(session).add(event)
            record = _to_record(saved)
            logger.info(
                "Event created event_id=%s event_type=%s camera_id=%s track_id=%s "
                "person_id=%s similarity=%s",
                record.id,
                record.event_type.value,
                record.camera_id,
                record.track_id,
                record.person_id,
                record.similarity,
            )
            return record
        except Exception:
            with self._lock:
                # Allow retry after failed write.
                if self._last_emit.get(cooldown_key) == now_mono:
                    del self._last_emit[cooldown_key]
            logger.exception(
                "Event persistence failed camera_id=%s track_id=%s event_type=%s",
                camera_id,
                result.track_id,
                event_type.value,
            )
            return None

    def get_event(self, event_id: str) -> EventRecord:
        with self._database.session() as session:
            row = EventRepository(session).get(event_id)
            if row is None:
                raise EventNotFoundError(event_id)
            return _to_record(row)

    def list_events(
        self,
        *,
        camera_id: str | None = None,
        person_id: str | None = None,
        event_type: EventType | str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        page: int = 1,
        page_size: int | None = None,
    ) -> EventListResult:
        if page < 1:
            raise EventValidationError("page must be >= 1")
        size = page_size if page_size is not None else self._config.default_page_size
        if size < 1 or size > self._config.max_page_size:
            raise EventValidationError(
                f"page_size must be between 1 and {self._config.max_page_size}"
            )
        parsed_type: EventType | None = None
        if event_type is not None:
            try:
                parsed_type = (
                    event_type if isinstance(event_type, EventType) else EventType(event_type)
                )
            except ValueError as exc:
                raise EventValidationError(f"Invalid event_type '{event_type}'") from exc
        if occurred_from is not None and occurred_to is not None and occurred_from > occurred_to:
            raise EventValidationError("'from' must be <= 'to'")

        offset = (page - 1) * size
        with self._database.session() as session:
            rows, total = EventRepository(session).list_events(
                camera_id=camera_id,
                person_id=person_id,
                event_type=parsed_type,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
                offset=offset,
                limit=size,
            )
            items = [_to_record(row) for row in rows]
        return EventListResult(items=items, page=page, page_size=size, total=total)

    def clear_cooldowns(self) -> None:
        """Test helper: reset in-memory cooldown state."""
        with self._lock:
            self._last_emit.clear()

    def purge_expired_events(self, *, now: datetime | None = None) -> int:
        """Delete events older than retention_days. Never deletes people or enrollments.

        Returns the number of deleted rows. No-op when retention is disabled.
        """
        if not self._config.retention_enabled:
            logger.info("Event retention disabled; skipping purge")
            return 0
        when = now or _utc_now()
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        cutoff = when - timedelta(days=self._config.retention_days)
        with self._database.session() as session:
            deleted = EventRepository(session).delete_older_than(cutoff)
        logger.info(
            "Event retention purge deleted=%s retention_days=%s cutoff=%s",
            deleted,
            self._config.retention_days,
            cutoff.isoformat(),
        )
        return deleted
