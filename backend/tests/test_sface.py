"""Unit and real-model tests for SFace embedding."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.core.config import PROJECT_ROOT
from app.vision.align import AlignedFace
from app.vision.embedder import FaceEmbedding
from app.vision.engine import CPU_PROVIDER, OnnxRuntimeEngine
from app.vision.exceptions import InferenceError, ModelLoadError, ModelNotFoundError
from app.vision.factory import create_face_embedder
from app.vision.sface import (
    SFACE_EMBEDDING_DIM,
    SFACE_INPUT_HEIGHT,
    SFACE_INPUT_WIDTH,
    SFaceConfig,
    SFaceEmbedder,
    preprocess_aligned_bgr,
)
from tests.helpers import IsolatedSettings

MODEL_PATH = PROJECT_ROOT / "models" / "face" / "sface" / "2021dec.onnx"

requires_sface = pytest.mark.skipif(
    not MODEL_PATH.is_file(),
    reason="SFace model is not installed; run python scripts/download_models.py",
)

# Repeated inference on the same blob must match within this absolute tolerance.
DETERMINISM_ATOL = 1e-6


class _CountingEngine:
    def __init__(self, inner: OnnxRuntimeEngine) -> None:
        self._inner = inner
        self.runs = 0

    @property
    def input_name(self) -> str:
        return self._inner.input_name

    @property
    def input_shape(self) -> tuple[int | None, ...]:
        return self._inner.input_shape

    @property
    def output_names(self) -> list[str]:
        return self._inner.output_names

    @property
    def providers(self) -> list[str]:
        return self._inner.providers

    def run(self, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        self.runs += 1
        return self._inner.run(inputs)


def _aligned_face(
    *,
    track_id: int = 1,
    fill: int = 120,
    noise: bool = True,
) -> AlignedFace:
    image = np.full((112, 112, 3), fill, dtype=np.uint8)
    if noise:
        rng = np.random.default_rng(track_id * 17 + fill)
        noise_arr = rng.integers(0, 40, size=image.shape, dtype=np.uint8)
        image = np.clip(image.astype(np.int16) + noise_arr, 0, 255).astype(np.uint8)
    return AlignedFace(
        image=image,
        width=112,
        height=112,
        source_track_id=track_id,
        transform=np.eye(2, 3, dtype=np.float64),
    )


def test_preprocess_layout_and_rgb_swap() -> None:
    image = np.zeros((112, 112, 3), dtype=np.uint8)
    image[:, :, 0] = 10  # B
    image[:, :, 1] = 20  # G
    image[:, :, 2] = 30  # R
    blob = preprocess_aligned_bgr(image)
    assert blob.shape == (1, 3, 112, 112)
    assert blob.dtype == np.float32
    # After BGR→RGB: channel0=R=30, channel1=G=20, channel2=B=10
    assert float(blob[0, 0, 0, 0]) == 30.0
    assert float(blob[0, 1, 0, 0]) == 20.0
    assert float(blob[0, 2, 0, 0]) == 10.0


def test_preprocess_rejects_non_bgr() -> None:
    with pytest.raises(InferenceError, match="HxWx3"):
        preprocess_aligned_bgr(np.zeros((112, 112), dtype=np.uint8))


def test_missing_model_fails_clearly() -> None:
    settings = IsolatedSettings(
        face_embedding_enabled=True,
        face_embedding_model_path="models/face/sface/missing.onnx",
    )
    with pytest.raises(ModelNotFoundError, match="SFace model not found"):
        create_face_embedder(settings)


def test_factory_disabled_returns_none() -> None:
    settings = IsolatedSettings(face_embedding_enabled=False)
    assert create_face_embedder(settings) is None


@requires_sface
def test_real_sface_loads_cpu_provider_and_shapes() -> None:
    engine = OnnxRuntimeEngine(MODEL_PATH)
    assert engine.providers[0] == CPU_PROVIDER
    assert engine.input_name == "data"
    assert engine.input_shape == (1, 3, 112, 112)
    assert "fc1" in engine.output_names
    embedder = SFaceEmbedder(engine)
    assert embedder.provider == CPU_PROVIDER


@requires_sface
def test_real_sface_rejects_wrong_input_name_via_config() -> None:
    engine = OnnxRuntimeEngine(MODEL_PATH)
    with pytest.raises(ModelLoadError, match="112"):
        SFaceEmbedder(engine, SFaceConfig(input_width=96, input_height=96))


@requires_sface
def test_embedding_dimension_dtype_finite_normalized() -> None:
    embedder = create_face_embedder(
        IsolatedSettings(
            face_embedding_enabled=True,
            face_embedding_model_path=str(MODEL_PATH),
        )
    )
    assert embedder is not None
    result = embedder.embed(_aligned_face())
    assert isinstance(result, FaceEmbedding)
    assert result.dimension == SFACE_EMBEDDING_DIM
    assert result.vector.shape == (SFACE_EMBEDDING_DIM,)
    assert result.vector.dtype == np.float32
    assert bool(np.isfinite(result.vector).all())
    assert result.normalized is True
    assert abs(float(np.linalg.norm(result.vector)) - 1.0) < 1e-5
    assert result.source_track_id == 1


@requires_sface
def test_embedding_determinism() -> None:
    embedder = create_face_embedder(
        IsolatedSettings(
            face_embedding_enabled=True,
            face_embedding_model_path=str(MODEL_PATH),
        )
    )
    assert embedder is not None
    face = _aligned_face(track_id=3, fill=140)
    first = embedder.embed(face)
    second = embedder.embed(face)
    assert np.allclose(first.vector, second.vector, atol=DETERMINISM_ATOL)
    assert first.dimension == second.dimension == SFACE_EMBEDDING_DIM


@requires_sface
def test_different_inputs_produce_different_embeddings() -> None:
    embedder = create_face_embedder(
        IsolatedSettings(
            face_embedding_enabled=True,
            face_embedding_model_path=str(MODEL_PATH),
        )
    )
    assert embedder is not None
    a = embedder.embed(_aligned_face(track_id=1, fill=40))
    b = embedder.embed(_aligned_face(track_id=2, fill=200))
    assert not np.allclose(a.vector, b.vector, atol=1e-3)


@requires_sface
def test_session_is_reused() -> None:
    engine = _CountingEngine(OnnxRuntimeEngine(MODEL_PATH))
    embedder = SFaceEmbedder(engine)
    embedder.embed(_aligned_face(track_id=1))
    embedder.embed(_aligned_face(track_id=2))
    assert engine.runs == 2
    assert embedder.call_count == 2


@requires_sface
def test_multiple_tracks_independent_embeddings() -> None:
    embedder = create_face_embedder(
        IsolatedSettings(
            face_embedding_enabled=True,
            face_embedding_model_path=str(MODEL_PATH),
        )
    )
    assert embedder is not None
    results = [embedder.embed(_aligned_face(track_id=tid, fill=80 + tid * 20)) for tid in (1, 2, 3)]
    assert [item.source_track_id for item in results] == [1, 2, 3]
    assert all(item.dimension == SFACE_EMBEDDING_DIM for item in results)


def test_invalid_model_file_fails(tmp_path: Path) -> None:
    bogus = tmp_path / "broken.onnx"
    bogus.write_bytes(b"not-an-onnx-model")
    with pytest.raises(ModelLoadError):
        OnnxRuntimeEngine(bogus)


@requires_sface
def test_input_size_constants_match_model() -> None:
    assert SFACE_INPUT_WIDTH == 112
    assert SFACE_INPUT_HEIGHT == 112
    assert SFACE_EMBEDDING_DIM == 128
