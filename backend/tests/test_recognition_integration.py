"""Integration: enrollment gallery → recognition; optional real SFace."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

from app.core.config import PROJECT_ROOT
from app.db.session import Database
from app.models import Base
from app.persons.embedding_codec import EMBEDDING_DIM
from app.services.enrollment import EnrollmentService
from app.services.person import PersonService
from app.vision.align import AlignedFace
from app.vision.embedder import FaceEmbedding
from app.vision.engine import OnnxRuntimeEngine
from app.vision.factory import create_face_recognizer, resolve_model_path
from app.vision.gallery_recognizer import GalleryFaceRecognizer
from app.vision.gallery_store import SqlAlchemyGalleryStore
from app.vision.sface import SFaceConfig, SFaceEmbedder
from app.vision.types import RecognitionReason, RecognitionStatus
from tests.helpers import IsolatedSettings

SFACE_PATH = PROJECT_ROOT / "models" / "face" / "sface" / "2021dec.onnx"
requires_sface = pytest.mark.skipif(
    not SFACE_PATH.is_file(),
    reason="SFace model is not installed; run python scripts/download_models.py",
)


def _unit(seed: float) -> list[float]:
    vector = np.full(EMBEDDING_DIM, seed, dtype=np.float32)
    vector[0] = seed + 1.0
    vector = vector / float(np.linalg.norm(vector))
    return vector.astype(np.float32).tolist()


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database(f"sqlite:///{(tmp_path / 'recog.db').as_posix()}")
    Base.metadata.create_all(db.engine)
    try:
        yield db
    finally:
        db.dispose()


def test_sqlite_gallery_inactive_ignored(database: Database) -> None:
    with database.session() as session:
        persons = PersonService(session)
        enrollments = EnrollmentService(session)
        active = persons.create_person("Active")
        inactive = persons.create_person("Inactive")
        enrollments.add_embedding(active.id, _unit(1.0), quality_accepted=True, normalized=True)
        enrollments.add_embedding(inactive.id, _unit(2.0), quality_accepted=True, normalized=True)
        persons.deactivate_person(inactive.id)

    recognizer = GalleryFaceRecognizer(SqlAlchemyGalleryStore(database), threshold=0.3)
    # Query equals inactive enrollment — must not match inactive person.
    inactive_vec = np.asarray(_unit(2.0), dtype=np.float32)
    result = recognizer.recognize(
        FaceEmbedding(
            vector=inactive_vec,
            dimension=128,
            source_track_id=9,
            normalized=True,
        )
    )
    assert result.person_id != inactive.id
    # Active gallery still present; inactive vector may be unknown vs active.
    if result.status is RecognitionStatus.MATCHED:
        assert result.person_id == active.id
    else:
        assert result.status is RecognitionStatus.UNKNOWN


def test_enroll_then_recognize_exact(database: Database) -> None:
    vector = _unit(7.0)
    with database.session() as session:
        persons = PersonService(session)
        enrollments = EnrollmentService(session)
        person = persons.create_person("Known")
        sample = enrollments.add_embedding(
            person.id, vector, quality_accepted=True, normalized=True
        )

    settings = IsolatedSettings(
        database_url=database.url,
        face_recognition_enabled=True,
        face_recognition_threshold=0.363,
    )
    recognizer = create_face_recognizer(settings, database)
    assert recognizer is not None
    result = recognizer.recognize(
        FaceEmbedding(
            vector=np.asarray(vector, dtype=np.float32),
            dimension=128,
            source_track_id=1,
            normalized=True,
        )
    )
    assert result.status is RecognitionStatus.MATCHED
    assert result.person_id == person.id
    assert result.enrollment_id == sample.id
    assert result.similarity is not None
    assert result.similarity >= 0.999


@requires_sface
def test_real_sface_enroll_and_rerecognize() -> None:
    """Same aligned crop → enroll → re-embed → match with measured similarity."""
    rng = np.random.default_rng(42)
    image = rng.integers(40, 200, size=(112, 112, 3), dtype=np.uint8)
    # Add mild structure so the crop is not pure noise flat.
    image[20:90, 30:80] = 180
    face = AlignedFace(
        image=image,
        width=112,
        height=112,
        source_track_id=1,
        transform=np.eye(2, 3, dtype=np.float64),
    )
    engine = OnnxRuntimeEngine(resolve_model_path(str(SFACE_PATH)), intra_op_num_threads=2)
    embedder = SFaceEmbedder(engine, SFaceConfig())
    first = embedder.embed(face)
    second = embedder.embed(face)

    db = Database("sqlite:///:memory:")
    Base.metadata.create_all(db.engine)
    try:
        with db.session() as session:
            persons = PersonService(session)
            enrollments = EnrollmentService(session)
            person = persons.create_person("SFace Subject")
            enrollments.add_embedding(
                person.id,
                first.vector.tolist(),
                quality_accepted=True,
                normalized=first.normalized,
            )
        recognizer = GalleryFaceRecognizer(SqlAlchemyGalleryStore(db), threshold=0.363)
        result = recognizer.recognize(second)
        assert result.status is RecognitionStatus.MATCHED
        assert result.person_id == person.id
        assert result.similarity is not None
        # Report/assert high similarity for identical aligned input.
        assert result.similarity >= 0.99
        print(f"REAL_SFACE_RECOGNITION_SIMILARITY={result.similarity:.8f}")
    finally:
        db.dispose()


def test_empty_gallery_reason(database: Database) -> None:
    settings = IsolatedSettings(
        database_url=database.url,
        face_recognition_enabled=True,
        face_recognition_threshold=0.363,
    )
    recognizer = create_face_recognizer(settings, database)
    assert recognizer is not None
    result = recognizer.recognize(
        FaceEmbedding(
            vector=np.asarray(_unit(1.0), dtype=np.float32),
            dimension=128,
            source_track_id=1,
            normalized=True,
        )
    )
    assert result.status is RecognitionStatus.UNKNOWN
    assert result.reason is RecognitionReason.GALLERY_EMPTY
