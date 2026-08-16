"""Unit tests for cosine gallery recognition (no camera / SFace / FastAPI)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.persons.embedding_codec import EMBEDDING_DIM
from app.persons.exceptions import InvalidEmbeddingError
from app.vision.embedder import FaceEmbedding
from app.vision.gallery_recognizer import (
    DEFAULT_RECOGNITION_THRESHOLD,
    GalleryEntry,
    GalleryFaceRecognizer,
    InMemoryGalleryStore,
)
from app.vision.similarity import cosine_similarity, dot_product_unit
from app.vision.types import RecognitionReason, RecognitionStatus


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


def test_cosine_equals_dot_for_unit_vectors() -> None:
    a = _unit(1.0)
    b = _unit(1.2)
    cos = cosine_similarity(a, b)
    dot = dot_product_unit(a, b)
    assert abs(cos - dot) < 1e-6


def test_exact_enrollment_matches() -> None:
    vector = _unit(2.0)
    store = InMemoryGalleryStore(
        [_entry("p1", "Ali", "e1", vector)],
    )
    recognizer = GalleryFaceRecognizer(store, threshold=0.363)
    result = recognizer.recognize(_embedding(vector))
    assert result.status is RecognitionStatus.MATCHED
    assert result.person_id == "p1"
    assert result.person_display_name == "Ali"
    assert result.enrollment_id == "e1"
    assert result.similarity is not None
    assert result.similarity >= 0.999


def test_similar_embedding_matches() -> None:
    base = _unit(3.0)
    query = base.copy()
    query[5] += 0.01
    query = query / float(np.linalg.norm(query))
    store = InMemoryGalleryStore([_entry("p1", "Sam", "e1", base)])
    recognizer = GalleryFaceRecognizer(store, threshold=0.9)
    result = recognizer.recognize(_embedding(query))
    assert result.status is RecognitionStatus.MATCHED
    assert result.person_id == "p1"
    assert result.similarity is not None
    assert result.similarity >= 0.9


def test_dissimilar_is_unknown() -> None:
    enrolled = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    enrolled[0] = 1.0
    query = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    query[1] = 1.0
    store = InMemoryGalleryStore([_entry("p1", "Sam", "e1", enrolled)])
    recognizer = GalleryFaceRecognizer(store, threshold=0.363)
    result = recognizer.recognize(_embedding(query))
    assert result.status is RecognitionStatus.UNKNOWN
    assert result.person_id is None
    assert result.reason is RecognitionReason.BELOW_THRESHOLD
    assert result.similarity is not None
    assert result.similarity < 0.363


def test_empty_gallery() -> None:
    recognizer = GalleryFaceRecognizer(InMemoryGalleryStore(), threshold=0.363)
    result = recognizer.recognize(_embedding(_unit(1.0)))
    assert result.status is RecognitionStatus.UNKNOWN
    assert result.reason is RecognitionReason.GALLERY_EMPTY


def test_multiple_samples_use_max_not_average() -> None:
    high = _unit(4.0)
    low = _unit(40.0)
    # Query equals high sample; low sample must not dilute the person score.
    store = InMemoryGalleryStore(
        [
            _entry("p1", "Max", "low", low),
            _entry("p1", "Max", "high", high),
        ]
    )
    recognizer = GalleryFaceRecognizer(store, threshold=0.5)
    result = recognizer.recognize(_embedding(high))
    assert result.status is RecognitionStatus.MATCHED
    assert result.enrollment_id == "high"
    assert result.similarity is not None
    assert result.similarity >= 0.999


def test_best_person_wins_across_gallery() -> None:
    a_vec = _unit(1.0)
    b_vec = _unit(2.0)
    store = InMemoryGalleryStore(
        [
            _entry("pa", "A", "ea", a_vec),
            _entry("pb", "B", "eb", b_vec),
        ]
    )
    # Construct query closer to B than A by using B itself.
    recognizer = GalleryFaceRecognizer(store, threshold=0.3)
    result = recognizer.recognize(_embedding(b_vec))
    assert result.person_id == "pb"
    assert result.person_display_name == "B"


def test_person_b_higher_than_person_a() -> None:
    """Person A sample ~0.70-ish vs Person B exact match → B wins."""
    a = _unit(1.0)
    b = _unit(2.0)
    # Query nearly B.
    query = b.copy()
    store = InMemoryGalleryStore(
        [
            _entry("pa", "A", "ea", a),
            _entry("pb", "B", "eb", b),
        ]
    )
    recognizer = GalleryFaceRecognizer(store, threshold=DEFAULT_RECOGNITION_THRESHOLD)
    result = recognizer.recognize(_embedding(query))
    assert result.person_id == "pb"
    sim_a = cosine_similarity(query, a)
    sim_b = cosine_similarity(query, b)
    assert sim_b > sim_a
    assert result.similarity == pytest.approx(sim_b)


def test_threshold_boundary_inclusive() -> None:
    base = _unit(5.0)
    store = InMemoryGalleryStore([_entry("p1", "Edge", "e1", base)])
    # Force exact threshold by mocking gallery entry to a known score via identical vectors.
    recognizer = GalleryFaceRecognizer(store, threshold=1.0)
    exact = recognizer.recognize(_embedding(base))
    assert exact.status is RecognitionStatus.MATCHED
    assert exact.similarity == pytest.approx(1.0)

    recognizer_strict = GalleryFaceRecognizer(store, threshold=0.999999)
    almost = base.copy()
    almost[0] += 0.05
    almost = almost / float(np.linalg.norm(almost))
    score = cosine_similarity(almost, base)
    if score >= 0.999999:
        pytest.skip("perturbation still above strict threshold")
    result = recognizer_strict.recognize(_embedding(almost))
    assert result.status is RecognitionStatus.UNKNOWN
    assert result.reason is RecognitionReason.BELOW_THRESHOLD

    # Inclusive boundary: set threshold to measured score → matched.
    at_boundary = GalleryFaceRecognizer(store, threshold=score)
    boundary = at_boundary.recognize(_embedding(almost))
    assert boundary.status is RecognitionStatus.MATCHED
    assert boundary.similarity == pytest.approx(score)


def test_invalid_query_dimension_nan_inf() -> None:
    store = InMemoryGalleryStore([_entry("p1", "X", "e1", _unit(1.0))])
    recognizer = GalleryFaceRecognizer(store, threshold=0.363)

    short = np.zeros(127, dtype=np.float32)
    result = recognizer.recognize(
        FaceEmbedding(vector=short, dimension=127, source_track_id=1, normalized=True)
    )
    assert result.status is RecognitionStatus.ERROR
    assert result.reason is RecognitionReason.INVALID_EMBEDDING

    nan_vec = _unit(1.0)
    nan_vec[0] = math.nan
    result_nan = recognizer.recognize(_embedding(nan_vec))
    assert result_nan.status is RecognitionStatus.ERROR

    inf_vec = _unit(1.0)
    inf_vec[0] = math.inf
    result_inf = recognizer.recognize(_embedding(inf_vec))
    assert result_inf.status is RecognitionStatus.ERROR


def test_cosine_rejects_bad_dims() -> None:
    with pytest.raises(InvalidEmbeddingError):
        cosine_similarity(np.zeros(127), _unit(1.0))
