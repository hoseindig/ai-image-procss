"""Face embedding protocol. Application code depends on this, not ONNX Runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from app.vision.align import AlignedFace


@dataclass(frozen=True)
class FaceEmbedding:
    """One face embedding. `source_track_id` is for pipeline tracing, not a person ID."""

    vector: NDArray[np.float32]
    dimension: int
    source_track_id: int
    normalized: bool


class FaceEmbedder(Protocol):
    def embed(self, face: AlignedFace) -> FaceEmbedding:
        """Produce a deterministic embedding from an aligned face crop."""
        ...
