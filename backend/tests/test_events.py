"""Unit/integration tests for event cooldown and persistence."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.session import Database
from app.events.types import EventType
from app.main import create_app
from app.models import Base
from app.services.event import EventService, EventServiceConfig
from app.vision.recognizer import RecognitionResult
from app.vision.types import RecognitionReason, RecognitionStatus
from tests.helpers import IsolatedSettings


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database(f"sqlite:///{(tmp_path / 'events.db').as_posix()}")
    Base.metadata.create_all(db.engine)
    try:
        yield db
    finally:
        db.dispose()


def _matched(
    track_id: int = 1,
    person_id: str = "person-a",
    enrollment_id: str = "enroll-a",
    similarity: float = 0.8,
) -> RecognitionResult:
    return RecognitionResult(
        status=RecognitionStatus.MATCHED,
        track_id=track_id,
        person_id=person_id,
        person_display_name="A",
        similarity=similarity,
        enrollment_id=enrollment_id,
    )


def _unknown(track_id: int = 2, similarity: float = 0.2) -> RecognitionResult:
    return RecognitionResult(
        status=RecognitionStatus.UNKNOWN,
        track_id=track_id,
        similarity=similarity,
        reason=RecognitionReason.BELOW_THRESHOLD,
    )


def _service(
    database: Database, *, recognized: float = 10.0, unknown: float = 10.0
) -> EventService:
    return EventService(
        database,
        EventServiceConfig(
            enabled=True,
            recognized_cooldown_seconds=recognized,
            unknown_cooldown_seconds=unknown,
            default_page_size=50,
            max_page_size=200,
        ),
    )


def test_first_recognized_creates_one_event(database: Database) -> None:
    service = _service(database)
    record = service.record_from_recognition("cam-1", _matched())
    assert record is not None
    assert record.event_type is EventType.RECOGNIZED
    assert record.person_id == "person-a"
    assert record.enrollment_id == "enroll-a"
    listed = service.list_events()
    assert listed.total == 1


def test_same_person_during_cooldown_suppressed(database: Database) -> None:
    service = _service(database, recognized=10.0)
    assert service.record_from_recognition("cam-1", _matched()) is not None
    assert service.record_from_recognition("cam-1", _matched(track_id=99)) is None
    assert service.list_events().total == 1


def test_same_person_after_cooldown_creates_new_event(database: Database) -> None:
    service = _service(database, recognized=0.05)
    assert service.record_from_recognition("cam-1", _matched()) is not None
    assert service.record_from_recognition("cam-1", _matched()) is None
    time.sleep(0.06)
    second = service.record_from_recognition("cam-1", _matched())
    assert second is not None
    assert service.list_events().total == 2


def test_person_a_then_person_b_two_events(database: Database) -> None:
    service = _service(database)
    assert service.record_from_recognition("cam-1", _matched(person_id="a")) is not None
    assert (
        service.record_from_recognition(
            "cam-1",
            _matched(person_id="b", enrollment_id="enroll-b", track_id=2),
        )
        is not None
    )
    assert service.list_events().total == 2


def test_unknown_cooldown(database: Database) -> None:
    service = _service(database, unknown=10.0)
    assert service.record_from_recognition("cam-1", _unknown(track_id=4)) is not None
    assert service.record_from_recognition("cam-1", _unknown(track_id=4)) is None
    assert service.list_events().total == 1


def test_unknown_after_cooldown(database: Database) -> None:
    service = _service(database, unknown=0.05)
    assert service.record_from_recognition("cam-1", _unknown(track_id=5)) is not None
    time.sleep(0.06)
    assert service.record_from_recognition("cam-1", _unknown(track_id=5)) is not None
    assert service.list_events().total == 2


def test_track_id_change_same_person_still_deduped(database: Database) -> None:
    service = _service(database)
    assert service.record_from_recognition("cam-1", _matched(track_id=1)) is not None
    assert service.record_from_recognition("cam-1", _matched(track_id=7)) is None


def test_cameras_independent(database: Database) -> None:
    service = _service(database)
    assert service.record_from_recognition("cam-1", _matched()) is not None
    assert service.record_from_recognition("cam-2", _matched()) is not None
    assert service.list_events().total == 2


def test_skipped_and_error_do_not_create_events(database: Database) -> None:
    service = _service(database)
    skipped = RecognitionResult(
        status=RecognitionStatus.SKIPPED,
        track_id=1,
        reason=RecognitionReason.QUALITY_REJECTED,
    )
    errored = RecognitionResult(
        status=RecognitionStatus.ERROR,
        track_id=1,
        reason=RecognitionReason.INVALID_EMBEDDING,
    )
    assert service.record_from_recognition("cam-1", skipped) is None
    assert service.record_from_recognition("cam-1", errored) is None
    assert service.list_events().total == 0


def test_list_ordering_and_filters(database: Database) -> None:
    service = _service(database, recognized=0.0, unknown=0.0)
    service.record_from_recognition("cam-1", _matched(person_id="a"))
    service.record_from_recognition("cam-1", _unknown(track_id=3))
    service.record_from_recognition("cam-2", _matched(person_id="b", enrollment_id="eb"))
    by_cam = service.list_events(camera_id="cam-1")
    assert by_cam.total == 2
    by_type = service.list_events(event_type=EventType.UNKNOWN_FACE)
    assert by_type.total == 1
    by_person = service.list_events(person_id="b")
    assert by_person.total == 1
    page = service.list_events(page=1, page_size=2)
    assert len(page.items) == 2
    assert page.total == 3
    # Newest first
    assert page.items[0].occurred_at >= page.items[1].occurred_at


def test_disabled_service_writes_nothing(database: Database) -> None:
    service = EventService(database, EventServiceConfig(enabled=False))
    assert service.record_from_recognition("cam-1", _matched()) is None
    assert service.list_events().total == 0


@pytest.fixture
def event_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    for key in (
        "DATABASE_URL",
        "FACE_DETECTION_ENABLED",
        "FACE_EMBEDDING_ENABLED",
        "FACE_RECOGNITION_ENABLED",
        "EVENT_LOGGING_ENABLED",
        "EVENT_RECOGNIZED_COOLDOWN_SECONDS",
        "EVENT_UNKNOWN_COOLDOWN_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)
    db_path = tmp_path / "api_events.db"
    settings: Settings = IsolatedSettings(
        app_env="test",
        database_url=f"sqlite:///{db_path.as_posix()}",
        face_detection_enabled=False,
        face_embedding_enabled=False,
        face_recognition_enabled=False,
        event_logging_enabled=True,
        event_recognized_cooldown_seconds=10.0,
        event_unknown_cooldown_seconds=10.0,
    )
    application = create_app(settings)
    with TestClient(application) as client:
        database = application.state.database
        Base.metadata.create_all(database.engine)
        service = application.state.event_service
        assert isinstance(service, EventService)
        service.record_from_recognition("default", _matched())
        service.record_from_recognition("default", _unknown(track_id=8))
        yield client


def test_events_api_list_and_get(event_client: TestClient) -> None:
    listed = event_client.get("/api/events")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert "embedding" not in listed.text.lower() or "embeddings" not in listed.text
    event_id = body["items"][0]["id"]
    detail = event_client.get(f"/api/events/{event_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == event_id
    filtered = event_client.get("/api/events", params={"event_type": "recognized"})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    missing = event_client.get("/api/events/00000000-0000-0000-0000-000000000099")
    assert missing.status_code == 404


def test_events_api_bad_page_size(event_client: TestClient) -> None:
    response = event_client.get("/api/events", params={"page_size": 9999})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "event_validation_error"
