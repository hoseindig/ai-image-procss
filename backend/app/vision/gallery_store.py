"""Load active enrollment samples for recognition (bounded, no N+1)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import Database
from app.models.person import EnrollmentSample, Person
from app.persons.embedding_codec import deserialize_embedding
from app.vision.gallery_recognizer import GalleryEntry


class SqlAlchemyGalleryStore:
    """One session per load; join active persons with their enrollment samples."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def load_active_entries(self) -> list[GalleryEntry]:
        with self._database.session() as session:
            return _load_entries(session)


def _load_entries(session: Session) -> list[GalleryEntry]:
    rows = session.execute(
        select(
            EnrollmentSample.id,
            EnrollmentSample.person_id,
            EnrollmentSample.embedding,
            Person.display_name,
        )
        .join(Person, Person.id == EnrollmentSample.person_id)
        .where(Person.active.is_(True))
    ).all()
    entries: list[GalleryEntry] = []
    for enrollment_id, person_id, blob, display_name in rows:
        vector = deserialize_embedding(blob)
        entries.append(
            GalleryEntry(
                person_id=str(person_id),
                display_name=str(display_name),
                enrollment_id=str(enrollment_id),
                vector=vector,
            )
        )
    return entries
