"""Person and enrollment service / API tests."""

from __future__ import annotations

import math
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.session import Database
from app.main import create_app
from app.models import Base
from app.models.person import EnrollmentSample, Person
from app.persons.embedding_codec import EMBEDDING_DIM, deserialize_embedding
from app.persons.exceptions import (
    EnrollmentQualityRejectedError,
    InvalidEmbeddingError,
    PersonConflictError,
    PersonInactiveError,
    PersonNotFoundError,
    PersonValidationError,
)
from app.services.enrollment import EnrollmentService
from app.services.person import PersonService


def _valid_embedding(seed: float = 1.0) -> list[float]:
    vector = np.full(EMBEDDING_DIM, seed, dtype=np.float32)
    vector = vector / float(np.linalg.norm(vector))
    return vector.astype(np.float32).tolist()


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database(f"sqlite:///{(tmp_path / 'persons.db').as_posix()}")
    Base.metadata.create_all(db.engine)
    try:
        yield db
    finally:
        db.dispose()


@pytest.fixture
def migrated_client(settings: Settings) -> Iterator[TestClient]:
    application = create_app(settings)
    with TestClient(application) as test_client:
        database = application.state.database
        Base.metadata.create_all(database.engine)
        yield test_client


def test_create_and_get_person(database: Database) -> None:
    with database.session() as session:
        service = PersonService(session)
        created = service.create_person("  Jane Doe  ")
        assert created.display_name == "Jane Doe"
        assert created.active is True
        assert created.enrollment_count == 0
        fetched = service.get_person(created.id)
        assert fetched.id == created.id
        assert fetched.display_name == "Jane Doe"


def test_duplicate_display_name_rejected(database: Database) -> None:
    with database.session() as session:
        service = PersonService(session)
        service.create_person("Alex")
        with pytest.raises(PersonConflictError):
            service.create_person("Alex")


def test_invalid_display_name_rejected(database: Database) -> None:
    with database.session() as session:
        service = PersonService(session)
        with pytest.raises(PersonValidationError):
            service.create_person("   ")
        with pytest.raises(PersonValidationError):
            service.create_person("x" * 101)


def test_list_update_activate_deactivate(database: Database) -> None:
    with database.session() as session:
        service = PersonService(session)
        person = service.create_person("Sam")
        listed = service.list_persons()
        assert len(listed) == 1
        updated = service.update_person(person.id, display_name="Sam Updated")
        assert updated.display_name == "Sam Updated"
        deactivated = service.deactivate_person(person.id)
        assert deactivated.active is False
        activated = service.activate_person(person.id)
        assert activated.active is True


def test_add_valid_embedding_and_metadata(database: Database) -> None:
    with database.session() as session:
        persons = PersonService(session)
        enrollments = EnrollmentService(session)
        person = persons.create_person("Pat")
        sample = enrollments.add_embedding(
            person.id,
            _valid_embedding(2.0),
            quality_accepted=True,
            normalized=True,
            face_width=120.0,
            face_height=130.0,
            sharpness=90.0,
            brightness=110.0,
            source_track_id=7,
        )
        assert sample.dimension == 128
        assert sample.face_width == 120.0
        assert "embedding" not in sample.model_dump()
        meta = enrollments.list_enrollments(person.id)
        assert len(meta) == 1
        assert meta[0].id == sample.id
        vector = enrollments.load_embedding_vector(person.id, sample.id)
        assert len(vector) == 128
        assert all(math.isfinite(v) for v in vector)


def test_reject_wrong_dim_nan_inf(database: Database) -> None:
    with database.session() as session:
        persons = PersonService(session)
        enrollments = EnrollmentService(session)
        person = persons.create_person("Reject")
        with pytest.raises(InvalidEmbeddingError):
            enrollments.add_embedding(
                person.id,
                [0.0] * 127,
                quality_accepted=True,
            )
        with pytest.raises(InvalidEmbeddingError):
            enrollments.add_embedding(
                person.id,
                [0.0] * 129,
                quality_accepted=True,
            )
        nan_vec = _valid_embedding()
        nan_vec[0] = math.nan
        with pytest.raises(InvalidEmbeddingError):
            enrollments.add_embedding(person.id, nan_vec, quality_accepted=True)
        inf_vec = _valid_embedding()
        inf_vec[0] = math.inf
        with pytest.raises(InvalidEmbeddingError):
            enrollments.add_embedding(person.id, inf_vec, quality_accepted=True)


def test_multiple_embeddings_independent(database: Database) -> None:
    with database.session() as session:
        persons = PersonService(session)
        enrollments = EnrollmentService(session)
        person = persons.create_person("Multi")
        first = enrollments.add_embedding(person.id, _valid_embedding(1.0), quality_accepted=True)
        second = enrollments.add_embedding(person.id, _valid_embedding(3.0), quality_accepted=True)
        assert first.id != second.id
        listed = enrollments.list_enrollments(person.id)
        assert len(listed) == 2
        refreshed = persons.get_person(person.id)
        assert refreshed.enrollment_count == 2


def test_quality_gate_and_inactive_person(database: Database) -> None:
    with database.session() as session:
        persons = PersonService(session)
        enrollments = EnrollmentService(session)
        person = persons.create_person("Gate")
        with pytest.raises(EnrollmentQualityRejectedError):
            enrollments.add_embedding(
                person.id,
                _valid_embedding(),
                quality_accepted=False,
            )
        persons.deactivate_person(person.id)
        with pytest.raises(PersonInactiveError):
            enrollments.add_embedding(
                person.id,
                _valid_embedding(),
                quality_accepted=True,
            )


def test_delete_enrollment_and_unknown_person(database: Database) -> None:
    with database.session() as session:
        persons = PersonService(session)
        enrollments = EnrollmentService(session)
        person = persons.create_person("DeleteMe")
        sample = enrollments.add_embedding(person.id, _valid_embedding(), quality_accepted=True)
        enrollments.delete_enrollment(person.id, sample.id)
        assert enrollments.list_enrollments(person.id) == []
        with pytest.raises(PersonNotFoundError):
            persons.get_person("00000000-0000-0000-0000-000000000000")


def test_rollback_on_invalid_enrollment(database: Database) -> None:
    with database.session() as session:
        persons = PersonService(session)
        enrollments = EnrollmentService(session)
        person = persons.create_person("Rollback")
        with pytest.raises(InvalidEmbeddingError):
            enrollments.add_embedding(
                person.id,
                [0.0] * 127,
                quality_accepted=True,
            )
        count = session.scalar(
            select(func.count())
            .select_from(EnrollmentSample)
            .where(EnrollmentSample.person_id == person.id)
        )
        assert count == 0


def test_serialization_preserves_db_blob(database: Database) -> None:
    original = np.asarray(_valid_embedding(5.0), dtype=np.float32)
    with database.session() as session:
        persons = PersonService(session)
        enrollments = EnrollmentService(session)
        person = persons.create_person("Blob")
        sample = enrollments.add_embedding(person.id, original.tolist(), quality_accepted=True)
        row = session.get(EnrollmentSample, sample.id)
        assert row is not None
        restored = deserialize_embedding(row.embedding)
        np.testing.assert_array_equal(restored, original)


def test_api_person_crud_and_enrollment_metadata(migrated_client: TestClient) -> None:
    create = migrated_client.post("/api/persons", json={"display_name": "API User"})
    assert create.status_code == 201
    person = create.json()
    person_id = person["id"]

    listed = migrated_client.get("/api/persons")
    assert listed.status_code == 200
    assert len(listed.json()["persons"]) == 1

    got = migrated_client.get(f"/api/persons/{person_id}")
    assert got.status_code == 200
    assert got.json()["display_name"] == "API User"

    patched = migrated_client.patch(
        f"/api/persons/{person_id}",
        json={"display_name": "API Renamed"},
    )
    assert patched.status_code == 200
    assert patched.json()["display_name"] == "API Renamed"

    enroll = migrated_client.post(
        f"/api/persons/{person_id}/enrollments",
        json={
            "embedding": _valid_embedding(4.0),
            "normalized": True,
            "quality": {
                "accepted": True,
                "face_width": 100.0,
                "face_height": 110.0,
                "sharpness": 80.0,
                "brightness": 120.0,
            },
            "source_track_id": 3,
        },
    )
    assert enroll.status_code == 201
    body = enroll.json()
    assert body["dimension"] == 128
    assert "embedding" not in body
    enrollment_id = body["id"]

    meta = migrated_client.get(f"/api/persons/{person_id}/enrollments")
    assert meta.status_code == 200
    assert len(meta.json()["enrollments"]) == 1
    assert "embedding" not in meta.json()["enrollments"][0]

    rejected = migrated_client.post(
        f"/api/persons/{person_id}/enrollments",
        json={
            "embedding": _valid_embedding(),
            "quality": {"accepted": False},
        },
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "enrollment_quality_rejected"

    bad_dim = migrated_client.post(
        f"/api/persons/{person_id}/enrollments",
        json={
            "embedding": [0.0] * 127,
            "quality": {"accepted": True},
        },
    )
    assert bad_dim.status_code == 422

    deleted = migrated_client.delete(f"/api/persons/{person_id}/enrollments/{enrollment_id}")
    assert deleted.status_code == 204

    deactivated = migrated_client.delete(f"/api/persons/{person_id}")
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False

    enroll_inactive = migrated_client.post(
        f"/api/persons/{person_id}/enrollments",
        json={
            "embedding": _valid_embedding(),
            "quality": {"accepted": True},
        },
    )
    assert enroll_inactive.status_code == 400
    assert enroll_inactive.json()["error"]["code"] == "person_inactive"

    missing = migrated_client.get("/api/persons/00000000-0000-0000-0000-000000000099")
    assert missing.status_code == 404


def test_api_duplicate_name_conflict(migrated_client: TestClient) -> None:
    assert migrated_client.post("/api/persons", json={"display_name": "Dup"}).status_code == 201
    conflict = migrated_client.post("/api/persons", json={"display_name": "Dup"})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "person_conflict"


def test_person_table_exists_after_create_all(database: Database) -> None:
    with database.session() as session:
        assert session.scalar(select(func.count()).select_from(Person)) == 0
