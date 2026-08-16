"""SFace embedding via ONNX Runtime. Independent of YuNet and recognition.

Preprocessing matches OpenCV FaceRecognizerSF::feature (face_recognize.cpp):

    dnn::blobFromImage(aligned, scalefactor=1.0, size=112x112,
                       mean=(0,0,0), swapRB=true, crop=false)

That is: BGR→RGB, float32, values left in roughly [0, 255], NCHW, no mean/std.

L2 normalization matches OpenCV FaceRecognizerSF::match, which normalizes both
feature vectors before cosine / L2 distance. Normalization is applied here so
stored vectors are comparison-ready; this phase does not run recognition.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from app.core.logging import get_logger
from app.vision.align import AlignedFace
from app.vision.embedder import FaceEmbedding
from app.vision.engine import CPU_PROVIDER, InferenceEngine
from app.vision.exceptions import InferenceError, ModelLoadError

logger = get_logger("app.vision")

SFACE_INPUT_WIDTH = 112
SFACE_INPUT_HEIGHT = 112
SFACE_EMBEDDING_DIM = 128
SFACE_INPUT_NAME = "data"
SFACE_OUTPUT_NAME = "fc1"


@dataclass(frozen=True)
class SFaceConfig:
    input_width: int = SFACE_INPUT_WIDTH
    input_height: int = SFACE_INPUT_HEIGHT
    embedding_dim: int = SFACE_EMBEDDING_DIM
    normalize: bool = True


class SFaceEmbedder:
    """FaceEmbedder implementation for OpenCV Zoo SFace 2021dec."""

    def __init__(self, engine: InferenceEngine, config: SFaceConfig | None = None) -> None:
        self._engine = engine
        self._config = config or SFaceConfig()
        self._call_count = 0
        _validate_sface_engine(engine, self._config)
        logger.info(
            "SFace embedder ready provider=%s input=%sx%s dim=%s normalize=%s",
            ", ".join(engine.providers),
            self._config.input_width,
            self._config.input_height,
            self._config.embedding_dim,
            self._config.normalize,
        )

    @property
    def provider(self) -> str:
        providers = self._engine.providers
        return providers[0] if providers else CPU_PROVIDER

    @property
    def call_count(self) -> int:
        """Number of successful embed() calls (tests verify session reuse)."""
        return self._call_count

    @property
    def config(self) -> SFaceConfig:
        return self._config

    def embed(self, face: AlignedFace) -> FaceEmbedding:
        blob = preprocess_aligned_bgr(
            face.image,
            width=self._config.input_width,
            height=self._config.input_height,
        )
        outputs = self._engine.run({self._engine.input_name: blob})
        if SFACE_OUTPUT_NAME in outputs:
            raw = outputs[SFACE_OUTPUT_NAME]
        elif len(outputs) == 1:
            raw = next(iter(outputs.values()))
        else:
            raise InferenceError(
                f"SFace output '{SFACE_OUTPUT_NAME}' missing; got {sorted(outputs)}"
            )
        vector = _extract_vector(raw, self._config.embedding_dim)
        if not np.isfinite(vector).all():
            raise InferenceError("SFace embedding contains non-finite values")
        normalized = False
        if self._config.normalize:
            vector = _l2_normalize(vector)
            normalized = True
        self._call_count += 1
        return FaceEmbedding(
            vector=vector,
            dimension=int(vector.shape[0]),
            source_track_id=face.source_track_id,
            normalized=normalized,
        )


def preprocess_aligned_bgr(
    image: NDArray[np.uint8],
    *,
    width: int = SFACE_INPUT_WIDTH,
    height: int = SFACE_INPUT_HEIGHT,
) -> NDArray[np.float32]:
    """BGR HxWx3 uint8 → NCHW float32 RGB blob (OpenCV blobFromImage equivalent)."""
    if image.ndim != 3 or image.shape[2] != 3:
        raise InferenceError("SFace embedding requires an HxWx3 BGR aligned face")
    working = image
    if working.shape[0] != height or working.shape[1] != width:
        import cv2

        working = np.asarray(
            cv2.resize(working, (width, height), interpolation=cv2.INTER_LINEAR),
            dtype=np.uint8,
        )
    rgb = working[:, :, ::-1]
    return np.ascontiguousarray(rgb.transpose(2, 0, 1)[np.newaxis], dtype=np.float32)


def _extract_vector(raw: NDArray[np.float32], expected_dim: int) -> NDArray[np.float32]:
    flat = np.asarray(raw, dtype=np.float32).reshape(-1)
    if flat.shape[0] != expected_dim:
        raise InferenceError(
            f"SFace embedding dimension mismatch: expected {expected_dim}, got {flat.shape[0]}"
        )
    return np.ascontiguousarray(flat)


def _l2_normalize(vector: NDArray[np.float32]) -> NDArray[np.float32]:
    norm = float(np.linalg.norm(vector))
    if norm <= 0.0:
        raise InferenceError("SFace embedding has zero L2 norm")
    return np.ascontiguousarray(vector / norm, dtype=np.float32)


def _validate_sface_engine(engine: InferenceEngine, config: SFaceConfig) -> None:
    providers = engine.providers
    if not providers or providers[0] != CPU_PROVIDER:
        raise ModelLoadError(
            f"SFace requires {CPU_PROVIDER} as the active provider, got {providers}"
        )
    if engine.input_name != SFACE_INPUT_NAME:
        raise ModelLoadError(
            f"SFace input name mismatch: expected '{SFACE_INPUT_NAME}', got '{engine.input_name}'"
        )
    shape = engine.input_shape
    if len(shape) != 4:
        raise ModelLoadError(f"SFace input rank must be 4 (NCHW), got {shape}")
    _n, channels, height, width = shape
    if channels not in {3, None}:
        raise ModelLoadError(f"SFace expects 3 input channels, got {shape}")
    if height not in {config.input_height, None} or width not in {config.input_width, None}:
        raise ModelLoadError(
            f"SFace expects input {config.input_width}x{config.input_height}, got {shape}"
        )
    if SFACE_OUTPUT_NAME not in engine.output_names and len(engine.output_names) != 1:
        raise ModelLoadError(
            f"SFace output '{SFACE_OUTPUT_NAME}' missing; got {engine.output_names}"
        )
