"""Integration: quality gate → alignment → SFace embedding."""

from __future__ import annotations

import time

import numpy as np
import pytest

from app.cameras.manager import CameraManager
from app.cameras.types import CameraConfig, Frame
from app.core.config import PROJECT_ROOT, Settings
from app.vision.align import AlignedFace
from app.vision.embedder import FaceEmbedding
from app.vision.runtime import DetectionRuntime
from app.vision.sface import SFACE_EMBEDDING_DIM
from app.vision.types import (
    DetectionSnapshot,
    EmbeddingSkipReason,
    EmbeddingStatus,
    FaceDetection,
)
from tests.fake_camera import FakeCameraSource
from tests.quality_helpers import textured_frame
from tests.yunet_helpers import sample_face

MODEL_PATH = PROJECT_ROOT / "models" / "face" / "sface" / "2021dec.onnx"

requires_sface = pytest.mark.skipif(
    not MODEL_PATH.is_file(),
    reason="SFace model is not installed; run python scripts/download_models.py",
)


class LargeFaceDetector:
    provider = "test"

    def detect(self, frame: Frame) -> list[FaceDetection]:
        return [sample_face(x=40, y=40, width=100, height=100, confidence=0.93)]


class TinyFaceDetector:
    provider = "test"

    def detect(self, frame: Frame) -> list[FaceDetection]:
        return [sample_face(x=10, y=10, width=20, height=20, confidence=0.9)]


class CountingEmbedder:
    provider = "fake"

    def __init__(self) -> None:
        self.calls = 0
        self.faces: list[AlignedFace] = []

    def embed(self, face: AlignedFace) -> FaceEmbedding:
        self.calls += 1
        self.faces.append(face)
        vector = np.zeros((SFACE_EMBEDDING_DIM,), dtype=np.float32)
        vector[0] = 1.0
        return FaceEmbedding(
            vector=vector,
            dimension=SFACE_EMBEDDING_DIM,
            source_track_id=face.source_track_id,
            normalized=True,
        )


class _TexturedFakeCamera(FakeCameraSource):
    def __init__(self, config: CameraConfig, face_box: tuple[int, int, int, int]) -> None:
        super().__init__(config)
        self._face_box = face_box

    def read(self) -> Frame | None:
        frame = super().read()
        if frame is None:
            return None
        textured = textured_frame(frame.width, frame.height, face_box=self._face_box)
        return Frame(
            data=textured.data,
            timestamp=frame.timestamp,
            width=frame.width,
            height=frame.height,
        )


def test_rejected_quality_does_not_invoke_embedder(settings: Settings) -> None:
    embedder = CountingEmbedder()
    manager = CameraManager(
        source_factory=lambda config: _TexturedFakeCamera(config, face_box=(10, 10, 20, 20))
    )
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=160, height=120, fps=10))
    enabled = settings.model_copy(
        update={
            "face_detection_enabled": True,
            "face_tracking_enabled": True,
            "face_quality_enabled": True,
            "face_alignment_enabled": True,
            "face_embedding_enabled": True,
            "face_quality_min_face_width": 80,
            "face_quality_min_face_height": 80,
        }
    )
    runtime = DetectionRuntime(TinyFaceDetector(), enabled, manager, embedder=embedder)
    try:
        manager.start("cam-1")
        runtime.attach("cam-1")
        snapshot = _wait_for_embeddings(runtime, "cam-1")
        assert snapshot.embeddings
        assert snapshot.embeddings[0].status is EmbeddingStatus.SKIPPED
        assert snapshot.embeddings[0].reason is EmbeddingSkipReason.QUALITY_REJECTED
        assert snapshot.embedded_count == 0
        assert embedder.calls == 0
        assert runtime.latest_embeddings("cam-1") == ()
    finally:
        runtime.shutdown()
        manager.shutdown()


def test_alignment_unavailable_skips_embedder(settings: Settings) -> None:
    embedder = CountingEmbedder()
    manager = CameraManager(
        source_factory=lambda config: _TexturedFakeCamera(config, face_box=(40, 40, 100, 100))
    )
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=320, height=240, fps=10))
    enabled = settings.model_copy(
        update={
            "face_detection_enabled": True,
            "face_tracking_enabled": True,
            "face_quality_enabled": True,
            "face_alignment_enabled": False,
            "face_embedding_enabled": True,
            "face_quality_min_sharpness": 0.0,
            "face_quality_min_face_width": 80,
            "face_quality_min_face_height": 80,
        }
    )
    runtime = DetectionRuntime(LargeFaceDetector(), enabled, manager, embedder=embedder)
    try:
        manager.start("cam-1")
        runtime.attach("cam-1")
        snapshot = _wait_for_embeddings(runtime, "cam-1")
        assert snapshot.embeddings
        assert snapshot.embeddings[0].status is EmbeddingStatus.SKIPPED
        assert snapshot.embeddings[0].reason is EmbeddingSkipReason.ALIGNMENT_UNAVAILABLE
        assert embedder.calls == 0
    finally:
        runtime.shutdown()
        manager.shutdown()


def test_accepted_face_invokes_embedder(settings: Settings) -> None:
    embedder = CountingEmbedder()
    manager = CameraManager(
        source_factory=lambda config: _TexturedFakeCamera(config, face_box=(40, 40, 100, 100))
    )
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=320, height=240, fps=10))
    enabled = settings.model_copy(
        update={
            "face_detection_enabled": True,
            "face_tracking_enabled": True,
            "face_quality_enabled": True,
            "face_alignment_enabled": True,
            "face_embedding_enabled": True,
            "face_quality_min_sharpness": 60,
            "face_quality_min_face_width": 80,
            "face_quality_min_face_height": 80,
        }
    )
    runtime = DetectionRuntime(LargeFaceDetector(), enabled, manager, embedder=embedder)
    try:
        manager.start("cam-1")
        runtime.attach("cam-1")
        snapshot = _wait_for_generated(runtime, "cam-1")
        assert snapshot.embeddings[0].status is EmbeddingStatus.GENERATED
        assert snapshot.embeddings[0].dimension == SFACE_EMBEDDING_DIM
        assert snapshot.embedded_count == 1
        assert embedder.calls >= 1
        vectors = runtime.latest_embeddings("cam-1")
        assert len(vectors) == 1
        assert vectors[0].source_track_id == 1
    finally:
        runtime.shutdown()
        manager.shutdown()


@requires_sface
def test_real_sface_pipeline_embedding(settings: Settings) -> None:
    from app.vision.factory import create_face_embedder

    embedder = create_face_embedder(
        settings.model_copy(
            update={
                "face_embedding_enabled": True,
                "face_embedding_model_path": str(MODEL_PATH),
            }
        )
    )
    assert embedder is not None
    manager = CameraManager(
        source_factory=lambda config: _TexturedFakeCamera(config, face_box=(40, 40, 100, 100))
    )
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=320, height=240, fps=10))
    enabled = settings.model_copy(
        update={
            "face_detection_enabled": True,
            "face_tracking_enabled": True,
            "face_quality_enabled": True,
            "face_alignment_enabled": True,
            "face_embedding_enabled": True,
            "face_quality_min_sharpness": 60,
            "face_quality_min_face_width": 80,
            "face_quality_min_face_height": 80,
        }
    )
    runtime = DetectionRuntime(LargeFaceDetector(), enabled, manager, embedder=embedder)
    try:
        manager.start("cam-1")
        runtime.attach("cam-1")
        snapshot = _wait_for_generated(runtime, "cam-1")
        assert snapshot.embeddings[0].dimension == SFACE_EMBEDDING_DIM
        vectors = runtime.latest_embeddings("cam-1")
        assert len(vectors) == 1
        assert vectors[0].dimension == SFACE_EMBEDDING_DIM
        assert bool(np.isfinite(vectors[0].vector).all())
        assert abs(float(np.linalg.norm(vectors[0].vector)) - 1.0) < 1e-5
    finally:
        runtime.shutdown()
        manager.shutdown()


def test_runtime_shutdown_stops_worker(settings: Settings) -> None:
    embedder = CountingEmbedder()
    manager = CameraManager(
        source_factory=lambda config: _TexturedFakeCamera(config, face_box=(40, 40, 100, 100))
    )
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=320, height=240, fps=10))
    enabled = settings.model_copy(
        update={
            "face_detection_enabled": True,
            "face_tracking_enabled": True,
            "face_quality_enabled": True,
            "face_alignment_enabled": True,
        }
    )
    runtime = DetectionRuntime(LargeFaceDetector(), enabled, manager, embedder=embedder)
    manager.start("cam-1")
    runtime.attach("cam-1")
    _wait_for_generated(runtime, "cam-1")
    runtime.shutdown()
    manager.shutdown()
    assert runtime.latest("cam-1") is None


def _wait_for_embeddings(runtime: DetectionRuntime, camera_id: str) -> DetectionSnapshot:
    deadline = time.monotonic() + 2.0
    latest = runtime.latest(camera_id)
    while time.monotonic() < deadline:
        latest = runtime.latest(camera_id)
        if latest is not None and latest.embeddings:
            return latest
        time.sleep(0.01)
    assert latest is not None
    return latest


def _wait_for_generated(runtime: DetectionRuntime, camera_id: str) -> DetectionSnapshot:
    deadline = time.monotonic() + 2.0
    latest = runtime.latest(camera_id)
    while time.monotonic() < deadline:
        latest = runtime.latest(camera_id)
        if (
            latest is not None
            and latest.embeddings
            and latest.embeddings[0].status is EmbeddingStatus.GENERATED
        ):
            return latest
        time.sleep(0.01)
    assert latest is not None
    return latest
