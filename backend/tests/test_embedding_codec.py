"""Unit tests for embedding binary codec."""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.persons.embedding_codec import (
    EMBEDDING_BYTE_LENGTH,
    EMBEDDING_DIM,
    deserialize_embedding,
    serialize_embedding,
    validate_embedding_values,
)
from app.persons.exceptions import InvalidEmbeddingError


def _unit_vector() -> np.ndarray:
    vector = np.arange(EMBEDDING_DIM, dtype=np.float32)
    return vector / float(np.linalg.norm(vector))


def test_serialize_round_trip_preserves_values() -> None:
    original = _unit_vector()
    blob = serialize_embedding(original)
    assert len(blob) == EMBEDDING_BYTE_LENGTH
    restored = deserialize_embedding(blob)
    np.testing.assert_array_equal(restored, original.astype(np.float32))


def test_reject_wrong_dimensions() -> None:
    with pytest.raises(InvalidEmbeddingError, match="exactly 128"):
        validate_embedding_values(np.zeros(127, dtype=np.float32))
    with pytest.raises(InvalidEmbeddingError, match="exactly 128"):
        validate_embedding_values(np.zeros(129, dtype=np.float32))


def test_reject_nan_and_inf() -> None:
    nan_vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    nan_vec[0] = math.nan
    with pytest.raises(InvalidEmbeddingError, match="finite"):
        validate_embedding_values(nan_vec)

    inf_vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    inf_vec[1] = math.inf
    with pytest.raises(InvalidEmbeddingError, match="finite"):
        validate_embedding_values(inf_vec)


def test_reject_bad_blob_length() -> None:
    with pytest.raises(InvalidEmbeddingError, match="512 bytes"):
        deserialize_embedding(b"\x00" * 100)
