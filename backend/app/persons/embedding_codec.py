"""Lossless float32 little-endian serialization for gallery embeddings.

Format (documented contract):
- Exactly 128 IEEE-754 float32 values
- Little-endian byte order
- Contiguous binary blob of 512 bytes
- No header, no length prefix, no JSON

Round-trip via ``serialize_embedding`` / ``deserialize_embedding`` preserves
values bit-exactly for finite float32 inputs (sufficient for cosine similarity).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from app.persons.exceptions import InvalidEmbeddingError

EMBEDDING_DIM = 128
EMBEDDING_DTYPE = np.dtype("<f4")  # little-endian float32
EMBEDDING_BYTE_LENGTH = EMBEDDING_DIM * EMBEDDING_DTYPE.itemsize  # 512


def validate_embedding_values(
    values: Sequence[float] | NDArray[np.floating],
) -> NDArray[np.float32]:
    """Validate dimension and finiteness; return a 1-D float32 copy (host endian)."""
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise InvalidEmbeddingError("Embedding must be a numeric vector") from exc
    if array.ndim != 1:
        raise InvalidEmbeddingError(
            f"Embedding must be 1-dimensional, got shape {tuple(array.shape)}"
        )
    if array.shape[0] != EMBEDDING_DIM:
        raise InvalidEmbeddingError(
            f"Embedding must have exactly {EMBEDDING_DIM} dimensions, got {array.shape[0]}"
        )
    if not np.isfinite(array).all():
        raise InvalidEmbeddingError("Embedding must contain only finite values (no NaN/Inf)")
    return np.asarray(array, dtype=np.float32)


def serialize_embedding(values: Sequence[float] | NDArray[np.floating]) -> bytes:
    """Encode a validated 128-D vector as a 512-byte little-endian float32 blob."""
    vector = validate_embedding_values(values)
    blob = vector.astype(EMBEDDING_DTYPE, copy=False).tobytes(order="C")
    if len(blob) != EMBEDDING_BYTE_LENGTH:
        raise InvalidEmbeddingError(
            f"Serialized embedding must be {EMBEDDING_BYTE_LENGTH} bytes, got {len(blob)}"
        )
    return blob


def deserialize_embedding(blob: bytes) -> NDArray[np.float32]:
    """Decode a 512-byte little-endian float32 blob to a float32 vector."""
    if not isinstance(blob, (bytes, bytearray, memoryview)):
        raise InvalidEmbeddingError("Embedding blob must be bytes")
    raw = bytes(blob)
    if len(raw) != EMBEDDING_BYTE_LENGTH:
        raise InvalidEmbeddingError(
            f"Embedding blob must be {EMBEDDING_BYTE_LENGTH} bytes, got {len(raw)}"
        )
    vector = np.frombuffer(raw, dtype=EMBEDDING_DTYPE).astype(np.float32, copy=True)
    return validate_embedding_values(vector)
