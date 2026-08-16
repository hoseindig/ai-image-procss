"""In-memory face enrollment session state. No images or embeddings stored here."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from uuid import uuid4

from app.vision.types import QualityRejectionReason


class EnrollmentSessionState(StrEnum):
    STARTING = "starting"
    WAITING_FOR_FACE = "waiting_for_face"
    FACE_DETECTED = "face_detected"
    MULTIPLE_FACES = "multiple_faces"
    QUALITY_REJECTED = "quality_rejected"
    READY = "ready"
    CAPTURING = "capturing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class EnrollmentSessionRecord:
    id: str
    person_id: str
    camera_id: str
    state: EnrollmentSessionState = EnrollmentSessionState.STARTING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    track_id: int | None = None
    quality_reasons: list[QualityRejectionReason] = field(default_factory=list)
    message: str | None = None
    error_code: str | None = None
    enrollment_id: str | None = None
    face_width: float | None = None
    face_height: float | None = None
    sharpness: float | None = None
    brightness: float | None = None


class EnrollmentSessionStore:
    """Process-local session registry. Capacity is small; sessions expire."""

    def __init__(self, *, ttl_seconds: float = 1800.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._lock = RLock()
        self._sessions: dict[str, EnrollmentSessionRecord] = {}

    def create(self, *, person_id: str, camera_id: str) -> EnrollmentSessionRecord:
        self._purge_expired()
        session = EnrollmentSessionRecord(
            id=str(uuid4()),
            person_id=person_id,
            camera_id=camera_id,
            state=EnrollmentSessionState.STARTING,
        )
        with self._lock:
            self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> EnrollmentSessionRecord | None:
        self._purge_expired()
        with self._lock:
            return self._sessions.get(session_id)

    def update(self, session: EnrollmentSessionRecord) -> EnrollmentSessionRecord:
        session.updated_at = datetime.now(UTC)
        with self._lock:
            self._sessions[session.id] = session
        return session

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def _purge_expired(self) -> None:
        now = datetime.now(UTC)
        with self._lock:
            expired = [
                key
                for key, session in self._sessions.items()
                if (now - session.updated_at).total_seconds() > self._ttl_seconds
            ]
            for key in expired:
                self._sessions.pop(key, None)
