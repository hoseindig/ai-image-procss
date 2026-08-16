"""Enrollment session lifecycle tests. Uses fakes; no webcam required."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.cameras.manager import CameraManager
from app.cameras.types import CameraConfig
from app.core.config import Settings
from app.db.session import Database
from app.main import create_app
from app.models import Base
from app.persons.embedding_codec import EMBEDDING_DIM
from app.persons.enrollment_session import EnrollmentSessionState, EnrollmentSessionStore
from app.persons.exceptions import (
    EnrollmentCaptureNotReadyError,
    EnrollmentSessionConflictError,
    EnrollmentSessionNotFoundError,
    PersonInactiveError,
)
from app.services.enrollment import EnrollmentService
from app.services.enrollment_session import EnrollmentSessionService
from app.services.person import PersonService
from app.vision.embedder import FaceEmbedding
from app.vision.runtime import DetectionRuntime
from app.vision.types import (
    BoundingBox,
    DetectionSnapshot,
    EmbeddingInfo,
    EmbeddingStatus,
    FaceLandmarks,
    FaceQuality,
    FaceTrack,
    Point,
    QualityRejectionReason,
    TrackState,
)
from tests.fake_camera import FakeCameraSource

SessionStack = tuple[EnrollmentSessionService, "FakeRuntime", PersonService]


def _valid_embedding(seed: float = 1.0) -> np.ndarray:
    vector = np.full(EMBEDDING_DIM, seed, dtype=np.float32)
    return (vector / float(np.linalg.norm(vector))).astype(np.float32)


def _landmarks() -> FaceLandmarks:
    return FaceLandmarks(
        left_eye=Point(x=20, y=20),
        right_eye=Point(x=40, y=20),
        nose=Point(x=30, y=30),
        left_mouth=Point(x=22, y=40),
        right_mouth=Point(x=38, y=40),
    )


def _track(track_id: int = 1, *, state: TrackState = TrackState.CONFIRMED) -> FaceTrack:
    return FaceTrack(
        track_id=track_id,
        bounding_box=BoundingBox(x=10, y=10, width=80, height=80),
        confidence=0.9,
        landmarks=_landmarks(),
        age_frames=5,
        missed_frames=0,
        state=state,
    )


def _quality(
    track_id: int = 1,
    *,
    accepted: bool = True,
    reasons: list[QualityRejectionReason] | None = None,
) -> FaceQuality:
    return FaceQuality(
        track_id=track_id,
        accepted=accepted,
        reasons=reasons or [],
        face_width=80,
        face_height=80,
        sharpness=100.0,
        brightness=120.0,
        landmarks_valid=True,
    )


def _snapshot(
    *,
    tracks: list[FaceTrack],
    qualities: list[FaceQuality] | None = None,
    aligned_track_ids: list[int] | None = None,
    embeddings: list[EmbeddingInfo] | None = None,
) -> DetectionSnapshot:
    return DetectionSnapshot(
        camera_id="default",
        timestamp=datetime.now(UTC),
        tracks=tracks,
        qualities=qualities or [],
        embeddings=embeddings or [],
        aligned_track_ids=aligned_track_ids or [],
        aligned_count=len(aligned_track_ids or []),
        embedded_count=sum(
            1 for item in (embeddings or []) if item.status is EmbeddingStatus.GENERATED
        ),
    )


class FakeRuntime:
    def __init__(self) -> None:
        self.embedding_enabled = True
        self._snapshot: DetectionSnapshot | None = None
        self._embeddings: tuple[FaceEmbedding, ...] = ()

    def latest(self, camera_id: str) -> DetectionSnapshot | None:
        return self._snapshot

    def latest_embeddings(self, camera_id: str) -> tuple[FaceEmbedding, ...]:
        return self._embeddings


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database(f"sqlite:///{(tmp_path / 'enroll_session.db').as_posix()}")
    Base.metadata.create_all(db.engine)
    try:
        yield db
    finally:
        db.dispose()


@pytest.fixture
def camera_manager() -> CameraManager:
    def factory(config: CameraConfig) -> FakeCameraSource:
        return FakeCameraSource(config)

    manager = CameraManager(source_factory=factory)
    manager.register(
        CameraConfig(camera_id="default", name="Fake USB", width=64, height=48, fps=10)
    )
    manager.start("default")
    return manager


@pytest.fixture
def session_stack(database: Database, camera_manager: CameraManager) -> Iterator[SessionStack]:
    runtime = FakeRuntime()
    store = EnrollmentSessionStore()
    with database.session() as session:
        persons = PersonService(session)
        enrollments = EnrollmentService(session)
        service = EnrollmentSessionService(
            store,
            persons,
            enrollments,
            camera_manager,
            runtime,  # type: ignore[arg-type]
            default_camera_id="default",
        )
        yield service, runtime, persons


def test_start_requires_active_person(session_stack: SessionStack) -> None:
    service, _runtime, persons = session_stack
    person = persons.create_person("Inactive")
    persons.deactivate_person(person.id)
    with pytest.raises(PersonInactiveError):
        service.start_session(person.id)


def test_waiting_for_face(session_stack: SessionStack) -> None:
    service, runtime, persons = session_stack
    person = persons.create_person("Ali")
    runtime._snapshot = _snapshot(tracks=[])
    status = service.start_session(person.id)
    assert status.state is EnrollmentSessionState.WAITING_FOR_FACE


def test_multiple_faces(session_stack: SessionStack) -> None:
    service, runtime, persons = session_stack
    person = persons.create_person("Ali")
    runtime._snapshot = _snapshot(tracks=[_track(1), _track(2)])
    status = service.start_session(person.id)
    assert status.state is EnrollmentSessionState.MULTIPLE_FACES
    assert status.error_code == "multiple_faces"


def test_quality_rejected(session_stack: SessionStack) -> None:
    service, runtime, persons = session_stack
    person = persons.create_person("Ali")
    runtime._snapshot = _snapshot(
        tracks=[_track(1)],
        qualities=[_quality(1, accepted=False, reasons=[QualityRejectionReason.FACE_TOO_SMALL])],
    )
    status = service.start_session(person.id)
    assert status.state is EnrollmentSessionState.QUALITY_REJECTED
    assert status.error_code == "face_too_small"
    assert "closer" in (status.message or "").lower()


def test_missing_alignment_stays_face_detected(session_stack: SessionStack) -> None:
    service, runtime, persons = session_stack
    person = persons.create_person("Ali")
    runtime._snapshot = _snapshot(
        tracks=[_track(1)],
        qualities=[_quality(1)],
        aligned_track_ids=[],
    )
    status = service.start_session(person.id)
    assert status.state is EnrollmentSessionState.FACE_DETECTED
    assert status.error_code == "alignment_unavailable"


def test_ready_and_capture_success(session_stack: SessionStack) -> None:
    service, runtime, persons = session_stack
    person = persons.create_person("Ali")
    vector = _valid_embedding(2.0)
    runtime._snapshot = _snapshot(
        tracks=[_track(7)],
        qualities=[_quality(7)],
        aligned_track_ids=[7],
        embeddings=[
            EmbeddingInfo(
                track_id=7,
                status=EmbeddingStatus.GENERATED,
                dimension=EMBEDDING_DIM,
                normalized=True,
            )
        ],
    )
    runtime._embeddings = (
        FaceEmbedding(vector=vector, dimension=EMBEDDING_DIM, source_track_id=7, normalized=True),
    )
    status = service.start_session(person.id)
    assert status.state is EnrollmentSessionState.READY
    captured = service.capture(person.id, status.id)
    assert captured.state is EnrollmentSessionState.COMPLETED
    assert captured.enrollment_id is not None
    refreshed = persons.get_person(person.id)
    assert refreshed.enrollment_count == 1


def test_capture_not_ready(session_stack: SessionStack) -> None:
    service, runtime, persons = session_stack
    person = persons.create_person("Ali")
    runtime._snapshot = _snapshot(tracks=[])
    status = service.start_session(person.id)
    with pytest.raises(EnrollmentCaptureNotReadyError):
        service.capture(person.id, status.id)


def test_embedding_failure_not_ready(session_stack: SessionStack) -> None:
    service, runtime, persons = session_stack
    person = persons.create_person("Ali")
    runtime._snapshot = _snapshot(
        tracks=[_track(1)],
        qualities=[_quality(1)],
        aligned_track_ids=[1],
        embeddings=[
            EmbeddingInfo(
                track_id=1,
                status=EmbeddingStatus.FAILED,
                dimension=None,
                reason=None,
            )
        ],
    )
    status = service.start_session(person.id)
    assert status.state is EnrollmentSessionState.FACE_DETECTED
    with pytest.raises(EnrollmentCaptureNotReadyError):
        service.capture(person.id, status.id)


def test_cancel_and_unknown_session(session_stack: SessionStack) -> None:
    service, runtime, persons = session_stack
    person = persons.create_person("Ali")
    runtime._snapshot = _snapshot(tracks=[])
    status = service.start_session(person.id)
    cancelled = service.cancel(person.id, status.id)
    assert cancelled.state is EnrollmentSessionState.CANCELLED
    with pytest.raises(EnrollmentSessionNotFoundError):
        service.get_session(person.id, "missing")
    with pytest.raises(EnrollmentSessionConflictError):
        service.capture(person.id, status.id)


def test_camera_not_running(
    session_stack: SessionStack,
    camera_manager: CameraManager,
) -> None:
    service, runtime, persons = session_stack
    person = persons.create_person("Ali")
    camera_manager.stop("default")
    camera_manager.close("default")
    runtime._snapshot = _snapshot(
        tracks=[_track(1)], qualities=[_quality(1)], aligned_track_ids=[1]
    )
    status = service.start_session(person.id)
    assert status.state is EnrollmentSessionState.FAILED
    assert status.error_code == "camera_not_running"


def test_duplicate_capture_conflict(session_stack: SessionStack) -> None:
    service, runtime, persons = session_stack
    person = persons.create_person("Ali")
    vector = _valid_embedding(3.0)
    runtime._snapshot = _snapshot(
        tracks=[_track(1)],
        qualities=[_quality(1)],
        aligned_track_ids=[1],
        embeddings=[
            EmbeddingInfo(
                track_id=1,
                status=EmbeddingStatus.GENERATED,
                dimension=EMBEDDING_DIM,
                normalized=True,
            )
        ],
    )
    runtime._embeddings = (
        FaceEmbedding(vector=vector, dimension=EMBEDDING_DIM, source_track_id=1, normalized=True),
    )
    status = service.start_session(person.id)
    service.capture(person.id, status.id)
    with pytest.raises(EnrollmentSessionConflictError):
        service.capture(person.id, status.id)


@pytest.fixture
def api_client(settings: Settings, tmp_path: Path) -> Iterator[TestClient]:
    settings = settings.model_copy(
        update={
            "database_url": f"sqlite:///{(tmp_path / 'api_enroll.db').as_posix()}",
            "face_embedding_enabled": True,
        }
    )

    def factory(config: CameraConfig) -> FakeCameraSource:
        return FakeCameraSource(config)

    manager = CameraManager(source_factory=factory)
    manager.register(
        CameraConfig(camera_id="default", name="Fake USB", width=64, height=48, fps=10)
    )
    application = create_app(settings, camera_manager=manager)
    with TestClient(application) as client:
        Base.metadata.create_all(application.state.database.engine)
        yield client


def test_api_enrollment_session_lifecycle(api_client: TestClient) -> None:
    created = api_client.post("/api/persons", json={"display_name": "API Person"})
    assert created.status_code == 201
    person_id = created.json()["id"]

    started = api_client.post(f"/api/persons/{person_id}/enrollment-sessions", json={})
    assert started.status_code == 201
    body = started.json()
    assert body["state"] == "failed"
    assert body["error_code"] == "camera_not_running"

    assert api_client.post("/api/cameras/default/start").status_code == 200

    vector = _valid_embedding(4.0)
    fake = FakeRuntime()
    fake._snapshot = _snapshot(
        tracks=[_track(9)],
        qualities=[_quality(9)],
        aligned_track_ids=[9],
        embeddings=[
            EmbeddingInfo(
                track_id=9,
                status=EmbeddingStatus.GENERATED,
                dimension=EMBEDDING_DIM,
                normalized=True,
            )
        ],
    )
    fake._embeddings = (
        FaceEmbedding(
            vector=vector,
            dimension=EMBEDDING_DIM,
            source_track_id=9,
            normalized=True,
        ),
    )
    app_state = cast(Any, api_client.app).state
    runtime = cast(DetectionRuntime, app_state.detection_runtime)
    runtime._embedder = cast(Any, object())
    runtime.latest = fake.latest  # type: ignore[method-assign]
    runtime.latest_embeddings = fake.latest_embeddings  # type: ignore[method-assign]

    session = api_client.post(f"/api/persons/{person_id}/enrollment-sessions", json={})
    assert session.status_code == 201
    session_id = session.json()["id"]
    assert session.json()["state"] == "ready"

    polled = api_client.get(f"/api/persons/{person_id}/enrollment-sessions/{session_id}")
    assert polled.status_code == 200
    assert polled.json()["state"] == "ready"

    captured = api_client.post(f"/api/persons/{person_id}/enrollment-sessions/{session_id}/capture")
    assert captured.status_code == 200
    assert captured.json()["state"] == "completed"
    assert captured.json()["enrollment_id"]

    enrollments = api_client.get(f"/api/persons/{person_id}/enrollments")
    assert enrollments.status_code == 200
    assert len(enrollments.json()["enrollments"]) == 1
    assert "embedding" not in enrollments.json()["enrollments"][0]

    cancelled_person = api_client.post("/api/persons", json={"display_name": "Cancel Me"})
    pid = cancelled_person.json()["id"]
    sess = api_client.post(f"/api/persons/{pid}/enrollment-sessions", json={}).json()
    deleted = api_client.delete(f"/api/persons/{pid}/enrollment-sessions/{sess['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["state"] == "cancelled"
