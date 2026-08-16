"""Deterministic recognition + event tests (TEST ONLY harness).

Covers Known/Unknown/threshold/events/cooldown/empty gallery/inactive person
using real GalleryFaceRecognizer + EventService (+ real SFace when model present).

Does not change production webcam behavior or quality gates.
"""

from __future__ import annotations

import math
import time
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import PROJECT_ROOT
from app.db.session import Database
from app.events.types import EventType
from app.main import create_app
from app.models import Base
from app.persons.embedding_codec import EMBEDDING_DIM
from app.services.enrollment import EnrollmentService
from app.services.event import EventService, EventServiceConfig
from app.services.person import PersonService
from app.services.recognition_test import (
    RecognitionTestDisabledError,
    RecognitionTestService,
)
from app.vision.align import AlignedFace
from app.vision.embedder import FaceEmbedding
from app.vision.engine import OnnxRuntimeEngine
from app.vision.factory import resolve_model_path
from app.vision.gallery_recognizer import (
    GalleryEntry,
    GalleryFaceRecognizer,
    InMemoryGalleryStore,
)
from app.vision.gallery_store import SqlAlchemyGalleryStore
from app.vision.sface import SFaceConfig, SFaceEmbedder
from app.vision.similarity import cosine_similarity
from app.vision.types import RecognitionReason, RecognitionStatus
from tests.helpers import IsolatedSettings

SFACE_PATH = PROJECT_ROOT / "models" / "face" / "sface" / "2021dec.onnx"
FACES_DIR = Path(__file__).resolve().parent / "fixtures" / "faces"
FACE_A = FACES_DIR / "synthetic_aligned_a.png"
FACE_B = FACES_DIR / "synthetic_aligned_b.png"

requires_sface = pytest.mark.skipif(
    not SFACE_PATH.is_file(),
    reason="SFace model is not installed; run python scripts/download_models.py",
)
requires_fixtures = pytest.mark.skipif(
    not (FACE_A.is_file() and FACE_B.is_file()),
    reason="Synthetic face fixtures missing; run generate_recognition_fixtures.py",
)

THRESHOLD = 0.363


def _unit(seed: float) -> np.ndarray:
    vector = np.full(EMBEDDING_DIM, seed, dtype=np.float32)
    vector[0] = seed + 1.0
    return vector / float(np.linalg.norm(vector))


def _embedding(vector: np.ndarray, track_id: int = 1) -> FaceEmbedding:
    return FaceEmbedding(
        vector=vector.astype(np.float32),
        dimension=EMBEDDING_DIM,
        source_track_id=track_id,
        normalized=True,
    )


def _entry(
    person_id: str,
    name: str,
    enrollment_id: str,
    vector: np.ndarray,
) -> GalleryEntry:
    return GalleryEntry(
        person_id=person_id,
        display_name=name,
        enrollment_id=enrollment_id,
        vector=vector.astype(np.float32),
    )


def _pair_at_cosine(target: float) -> tuple[np.ndarray, np.ndarray]:
    """Two unit vectors with cosine similarity exactly `target` (within float32)."""
    assert 0.0 <= target <= 1.0
    left = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    left[0] = 1.0
    right = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    right[0] = float(target)
    right[1] = float(math.sqrt(max(0.0, 1.0 - target * target)))
    right = right / float(np.linalg.norm(right))
    return left, right.astype(np.float32)


def _load_bgr(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    assert image is not None
    assert image.shape == (112, 112, 3)
    return image


def _sface_embedder() -> SFaceEmbedder:
    engine = OnnxRuntimeEngine(resolve_model_path(str(SFACE_PATH)), intra_op_num_threads=2)
    return SFaceEmbedder(engine, SFaceConfig())


def _aligned(image: np.ndarray, track_id: int = 1) -> AlignedFace:
    return AlignedFace(
        image=np.ascontiguousarray(image),
        width=112,
        height=112,
        source_track_id=track_id,
        transform=np.eye(2, 3, dtype=np.float64),
    )


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database(f"sqlite:///{(tmp_path / 'recog_test.db').as_posix()}")
    Base.metadata.create_all(db.engine)
    try:
        yield db
    finally:
        db.dispose()


def _event_service(
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


def _test_service(
    database: Database,
    embedder: SFaceEmbedder,
    *,
    enabled: bool = True,
    recognized_cd: float = 10.0,
    unknown_cd: float = 10.0,
) -> RecognitionTestService:
    return RecognitionTestService(
        enabled=enabled,
        embedder=embedder,
        recognizer=GalleryFaceRecognizer(
            SqlAlchemyGalleryStore(database),
            threshold=THRESHOLD,
        ),
        event_service=_event_service(database, recognized=recognized_cd, unknown=unknown_cd),
        recognition_threshold=THRESHOLD,
    )


# --- A / B: real SFace fixtures ---


@requires_sface
@requires_fixtures
def test_a_enrolled_face_recognized(database: Database) -> None:
    embedder = _sface_embedder()
    face_a = _load_bgr(FACE_A)
    enrollment = embedder.embed(_aligned(face_a, track_id=1))
    with database.session() as session:
        person = PersonService(session).create_person("Fixture A")
        EnrollmentService(session).add_embedding(
            person.id,
            enrollment.vector.tolist(),
            quality_accepted=True,
            normalized=enrollment.normalized,
        )
        person_id = person.id

    service = _test_service(database, embedder)
    outcome = service.recognize_aligned_bgr(face_a, camera_id="test", track_id=7)
    assert outcome.status == RecognitionStatus.MATCHED.value
    assert outcome.person_id == person_id
    assert outcome.similarity is not None
    assert outcome.similarity >= THRESHOLD
    assert outcome.event_created is True
    assert outcome.event_id is not None


@requires_sface
@requires_fixtures
def test_b_different_face_unknown(database: Database) -> None:
    embedder = _sface_embedder()
    face_a = _load_bgr(FACE_A)
    face_b = _load_bgr(FACE_B)
    enrollment = embedder.embed(_aligned(face_a))
    with database.session() as session:
        person = PersonService(session).create_person("Fixture A Only")
        EnrollmentService(session).add_embedding(
            person.id,
            enrollment.vector.tolist(),
            quality_accepted=True,
            normalized=enrollment.normalized,
        )

    service = _test_service(database, embedder)
    outcome = service.recognize_aligned_bgr(face_b, camera_id="test", track_id=3)
    assert outcome.status == RecognitionStatus.UNKNOWN.value
    assert outcome.person_id is None
    assert outcome.reason == RecognitionReason.BELOW_THRESHOLD.value
    assert outcome.similarity is not None
    assert outcome.similarity < THRESHOLD
    assert outcome.event_created is True


# --- C / D: real gallery recognizer with exact cosine construction ---


def test_c_similarity_below_threshold_unknown() -> None:
    enrolled, query = _pair_at_cosine(THRESHOLD - 0.05)
    store = InMemoryGalleryStore([_entry("p1", "Edge", "e1", enrolled)])
    recognizer = GalleryFaceRecognizer(store, threshold=THRESHOLD)
    result = recognizer.recognize(_embedding(query))
    assert result.status is RecognitionStatus.UNKNOWN
    assert result.reason is RecognitionReason.BELOW_THRESHOLD
    assert result.similarity is not None
    assert result.similarity < THRESHOLD
    assert result.similarity == pytest.approx(THRESHOLD - 0.05, abs=1e-5)


def test_d_similarity_at_threshold_recognized() -> None:
    enrolled, query = _pair_at_cosine(THRESHOLD)
    measured = float(cosine_similarity(enrolled, query))
    # float32 construction can land a ULP below the nominal target; inclusive
    # boundary is tested against the measured score (production uses >=).
    store = InMemoryGalleryStore([_entry("p1", "Edge", "e1", enrolled)])
    recognizer = GalleryFaceRecognizer(store, threshold=measured)
    result = recognizer.recognize(_embedding(query))
    assert result.status is RecognitionStatus.MATCHED
    assert result.person_id == "p1"
    assert result.similarity is not None
    assert result.similarity >= measured
    assert abs(measured - THRESHOLD) < 1e-5

    # Also assert production threshold accepts a score constructed >= 0.363.
    enrolled_hi, query_hi = _pair_at_cosine(THRESHOLD + 0.001)
    score_hi = float(cosine_similarity(enrolled_hi, query_hi))
    assert score_hi >= THRESHOLD
    prod = GalleryFaceRecognizer(
        InMemoryGalleryStore([_entry("p1", "Edge", "e1", enrolled_hi)]),
        threshold=THRESHOLD,
    )
    hi = prod.recognize(_embedding(query_hi))
    assert hi.status is RecognitionStatus.MATCHED
    assert hi.similarity is not None
    assert hi.similarity >= THRESHOLD


# --- E / F / G / H: events + cooldown via real EventService ---


def test_e_recognized_event_creation(database: Database) -> None:
    service = _event_service(database)
    from app.vision.recognizer import RecognitionResult

    result = RecognitionResult(
        status=RecognitionStatus.MATCHED,
        track_id=1,
        person_id="p-known",
        person_display_name="Known",
        similarity=0.8,
        enrollment_id="e1",
    )
    record = service.record_from_recognition("test", result)
    assert record is not None
    assert record.event_type is EventType.RECOGNIZED
    assert record.person_id == "p-known"
    assert record.similarity == 0.8


def test_f_recognized_cooldown(database: Database) -> None:
    service = _event_service(database, recognized=0.05)
    from app.vision.recognizer import RecognitionResult

    matched = RecognitionResult(
        status=RecognitionStatus.MATCHED,
        track_id=1,
        person_id="p-cd",
        person_display_name="CD",
        similarity=0.7,
        enrollment_id="e1",
    )
    assert service.record_from_recognition("test", matched) is not None
    assert service.record_from_recognition("test", matched) is None
    time.sleep(0.06)
    assert service.record_from_recognition("test", matched) is not None
    assert service.list_events().total == 2


def test_g_unknown_event_creation(database: Database) -> None:
    service = _event_service(database)
    from app.vision.recognizer import RecognitionResult

    unknown = RecognitionResult(
        status=RecognitionStatus.UNKNOWN,
        track_id=9,
        similarity=0.1,
        reason=RecognitionReason.BELOW_THRESHOLD,
    )
    record = service.record_from_recognition("test", unknown)
    assert record is not None
    assert record.event_type is EventType.UNKNOWN_FACE
    assert record.person_id is None


def test_h_unknown_cooldown(database: Database) -> None:
    service = _event_service(database, unknown=0.05)
    from app.vision.recognizer import RecognitionResult

    unknown = RecognitionResult(
        status=RecognitionStatus.UNKNOWN,
        track_id=11,
        similarity=0.2,
        reason=RecognitionReason.BELOW_THRESHOLD,
    )
    assert service.record_from_recognition("test", unknown) is not None
    assert service.record_from_recognition("test", unknown) is None
    time.sleep(0.06)
    assert service.record_from_recognition("test", unknown) is not None


# --- I / J ---


def test_i_empty_gallery() -> None:
    recognizer = GalleryFaceRecognizer(InMemoryGalleryStore(), threshold=THRESHOLD)
    result = recognizer.recognize(_embedding(_unit(1.0)))
    assert result.status is RecognitionStatus.UNKNOWN
    assert result.reason is RecognitionReason.GALLERY_EMPTY


def test_j_inactive_person_ignored(database: Database) -> None:
    with database.session() as session:
        persons = PersonService(session)
        enrollments = EnrollmentService(session)
        active = persons.create_person("Active")
        inactive = persons.create_person("Inactive")
        enrollments.add_embedding(
            active.id, _unit(1.0).tolist(), quality_accepted=True, normalized=True
        )
        enrollments.add_embedding(
            inactive.id, _unit(9.0).tolist(), quality_accepted=True, normalized=True
        )
        persons.deactivate_person(inactive.id)

    recognizer = GalleryFaceRecognizer(SqlAlchemyGalleryStore(database), threshold=0.3)
    # Query equals inactive enrollment vector — must not return inactive person.
    result = recognizer.recognize(_embedding(_unit(9.0)))
    assert result.person_id != inactive.id
    if result.status is RecognitionStatus.MATCHED:
        assert result.person_id == active.id
    else:
        assert result.status is RecognitionStatus.UNKNOWN


# --- Integration: embedding → gallery → recognition → event ---


@requires_sface
@requires_fixtures
def test_integration_embed_gallery_recognize_event(database: Database) -> None:
    embedder = _sface_embedder()
    face_a = _load_bgr(FACE_A)
    face_b = _load_bgr(FACE_B)
    vec_a = embedder.embed(_aligned(face_a))
    with database.session() as session:
        person = PersonService(session).create_person("Integration A")
        EnrollmentService(session).add_embedding(
            person.id,
            vec_a.vector.tolist(),
            quality_accepted=True,
            normalized=vec_a.normalized,
        )
        person_id = person.id

    service = _test_service(database, embedder, recognized_cd=0.05, unknown_cd=0.05)
    known = service.recognize_aligned_bgr(face_a, camera_id="test", track_id=1)
    assert known.status == "matched"
    assert known.person_id == person_id
    assert known.event_created is True
    assert (
        service.recognize_aligned_bgr(face_a, camera_id="test", track_id=1).event_created is False
    )
    time.sleep(0.06)
    assert service.recognize_aligned_bgr(face_a, camera_id="test", track_id=1).event_created is True

    unknown = service.recognize_aligned_bgr(face_b, camera_id="test", track_id=2)
    assert unknown.status == "unknown"
    assert unknown.person_id is None
    assert unknown.event_created is True
    assert (
        service.recognize_aligned_bgr(face_b, camera_id="test", track_id=2).event_created is False
    )


# --- Gate / API ---


def test_recognition_test_service_disabled_by_default(database: Database) -> None:
    class _DummyEmbedder:
        provider = "dummy"

        def embed(self, face: AlignedFace) -> FaceEmbedding:
            raise AssertionError("should not embed when disabled")

    service = RecognitionTestService(
        enabled=False,
        embedder=_DummyEmbedder(),  # structural FaceEmbedder stand-in
        recognizer=GalleryFaceRecognizer(InMemoryGalleryStore(), threshold=THRESHOLD),
        event_service=_event_service(database),
        recognition_threshold=THRESHOLD,
    )
    with pytest.raises(RecognitionTestDisabledError):
        service.recognize_aligned_bgr(np.zeros((112, 112, 3), dtype=np.uint8))


def test_api_recognize_forbidden_when_test_mode_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in (
        "RECOGNITION_TEST_MODE",
        "FACE_DETECTION_ENABLED",
        "FACE_EMBEDDING_ENABLED",
        "FACE_RECOGNITION_ENABLED",
        "EVENT_LOGGING_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)
    settings = IsolatedSettings(
        app_env="test",
        debug=True,
        database_url=f"sqlite:///{(tmp_path / 'api.db').as_posix()}",
        recognition_test_mode=False,
        face_detection_enabled=False,
        face_embedding_enabled=False,
        face_recognition_enabled=False,
        event_logging_enabled=False,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.post(
            "/api/test/recognize",
            files={"file": ("x.png", b"not-an-image", "image/png")},
            data={"camera_id": "test", "track_id": "1"},
        )
        assert response.status_code == 403, response.text
        body = response.json()
        assert body["detail"]["error"]["code"] == "recognition_test_disabled"


@requires_sface
@requires_fixtures
def test_api_recognize_ok_when_test_mode_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RECOGNITION_TEST_MODE", raising=False)
    db_path = tmp_path / "api_on.db"
    database_url = f"sqlite:///{db_path.as_posix()}"
    settings = IsolatedSettings(
        app_env="test",
        debug=True,
        database_url=database_url,
        recognition_test_mode=True,
        face_detection_enabled=False,
        face_embedding_enabled=True,
        face_embedding_model_path=str(SFACE_PATH),
        face_recognition_enabled=True,
        face_recognition_threshold=THRESHOLD,
        event_logging_enabled=True,
        event_recognized_cooldown_seconds=10.0,
        event_unknown_cooldown_seconds=10.0,
    )

    # Enroll before app start so TestClient typing stays clean.
    prep_db = Database(database_url)
    Base.metadata.create_all(prep_db.engine)
    prep_embedder = _sface_embedder()
    face_a = _load_bgr(FACE_A)
    vec = prep_embedder.embed(_aligned(face_a))
    with prep_db.session() as session:
        person = PersonService(session).create_person("API Fixture A")
        EnrollmentService(session).add_embedding(
            person.id,
            vec.vector.tolist(),
            quality_accepted=True,
            normalized=vec.normalized,
        )
        person_id = person.id
    prep_db.dispose()

    app = create_app(settings)
    with TestClient(app) as client:
        png_bytes = FACE_A.read_bytes()
        response = client.post(
            "/api/test/recognize",
            files={"file": ("synthetic_aligned_a.png", png_bytes, "image/png")},
            data={"camera_id": "test", "track_id": "1", "record_event": "true"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["test_only"] is True
        assert body["status"] == "matched"
        assert body["person_id"] == person_id
        assert body["similarity"] >= THRESHOLD
        assert body["event_created"] is True
        assert "embedding" not in body
        assert "vector" not in body

        response_b = client.post(
            "/api/test/recognize",
            files={"file": ("synthetic_aligned_b.png", FACE_B.read_bytes(), "image/png")},
            data={"camera_id": "test", "track_id": "2", "record_event": "true"},
        )
        assert response_b.status_code == 200
        body_b = response_b.json()
        assert body_b["status"] == "unknown"
        assert body_b["person_id"] is None
        assert body_b["reason"] == "below_threshold"
