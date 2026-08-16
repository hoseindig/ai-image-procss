"""Cosine similarity helpers for face recognition.

For two L2-normalized vectors (‖a‖ = ‖b‖ = 1), cosine similarity equals the
dot product:

    cos(a, b) = (a · b) / (‖a‖ ‖b‖) = a · b

This module always computes the full cosine formula so non-unit vectors remain
correct. Callers that store Phase-6 L2-normalized SFace embeddings may use
either form; tests verify numerical equivalence on unit vectors.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from app.persons.embedding_codec import validate_embedding_values
from app.persons.exceptions import InvalidEmbeddingError


def cosine_similarity(
    left: Sequence[float] | NDArray[np.floating],
    right: Sequence[float] | NDArray[np.floating],
) -> float:
    """Return cosine similarity in [-1, 1] with full float64 accumulation."""
    a = validate_embedding_values(left).astype(np.float64, copy=False)
    b = validate_embedding_values(right).astype(np.float64, copy=False)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        raise InvalidEmbeddingError("Cannot compute cosine similarity for a zero vector")
    return float(np.dot(a, b) / denom)


def dot_product_unit(
    left: Sequence[float] | NDArray[np.floating],
    right: Sequence[float] | NDArray[np.floating],
) -> float:
    """Dot product after validating 128-D finite vectors (equals cosine if unit)."""
    a = validate_embedding_values(left).astype(np.float64, copy=False)
    b = validate_embedding_values(right).astype(np.float64, copy=False)
    return float(np.dot(a, b))
