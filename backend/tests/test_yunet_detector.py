from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import PROJECT_ROOT
from app.vision.engine import CPU_PROVIDER, OnnxRuntimeEngine
from app.vision.exceptions import InferenceError, ModelLoadError, ModelNotFoundError
from app.vision.factory import create_face_detector, resolve_model_path
from app.vision.yunet import YuNetConfig, YuNetFaceDetector
from tests.fake_vision import FakeInferenceEngine
from tests.helpers import IsolatedSettings
from tests.yunet_helpers import blank_frame, empty_yunet_outputs


def _config(
    *,
    confidence_threshold: float = 0.7,
    nms_threshold: float = 0.3,
    input_width: int = 320,
    input_height: int = 320,
    max_faces: int = 10,
) -> YuNetConfig:
    return YuNetConfig(
        confidence_threshold=confidence_threshold,
        nms_threshold=nms_threshold,
        input_width=input_width,
        input_height=input_height,
        max_faces=max_faces,
    )


def test_missing_model_path_fails_clearly(tmp_path: Path) -> None:
    missing = tmp_path / "missing.onnx"
    settings = IsolatedSettings(
        face_detection_enabled=True,
        face_detection_model_path=str(missing),
        face_detection_input_width=320,
        face_detection_input_height=320,
    )
    with pytest.raises(ModelNotFoundError) as exc_info:
        create_face_detector(settings)
    assert str(missing.resolve()) in exc_info.value.message
    assert "YuNet model not found" in exc_info.value.message


def test_invalid_model_fails_to_load(tmp_path: Path) -> None:
    junk = tmp_path / "junk.onnx"
    junk.write_bytes(b"this is not an onnx model")
    with pytest.raises(ModelLoadError):
        OnnxRuntimeEngine(junk)


def test_relative_model_path_resolves_from_project_root() -> None:
    resolved = resolve_model_path("models/face/yunet/2023mar.onnx")
    assert resolved == (PROJECT_ROOT / "models" / "face" / "yunet" / "2023mar.onnx").resolve()


def test_detector_uses_cpu_provider_from_engine() -> None:
    engine = FakeInferenceEngine()
    detector = YuNetFaceDetector(engine, _config())
    assert detector.provider == CPU_PROVIDER


def test_detect_no_face() -> None:
    engine = FakeInferenceEngine()
    detector = YuNetFaceDetector(engine, _config())
    faces = detector.detect(blank_frame(640, 480))
    assert faces == []
    assert engine.last_input_shape == (1, 3, 320, 320)


def test_detect_one_face_maps_coordinates_and_landmarks() -> None:
    engine = FakeInferenceEngine()
    engine.set_faces([(8, 5, 5)])
    detector = YuNetFaceDetector(engine, _config())
    faces = detector.detect(blank_frame(640, 480))
    assert len(faces) == 1
    face = faces[0]
    assert face.confidence == 1.0
    # Model-space box (36, 36, 8, 8) on 320x320 → original 640x480.
    assert face.bounding_box.x == pytest.approx(72.0)
    assert face.bounding_box.y == pytest.approx(54.0)
    assert face.bounding_box.width == pytest.approx(16.0)
    assert face.bounding_box.height == pytest.approx(12.0)
    assert face.landmarks.left_eye.x == pytest.approx(80.0)
    assert face.landmarks.right_eye.x == pytest.approx(80.0)
    assert face.landmarks.nose.x == pytest.approx(80.0)
    assert face.landmarks.left_mouth.x == pytest.approx(80.0)
    assert face.landmarks.right_mouth.x == pytest.approx(80.0)


def test_detect_multiple_faces() -> None:
    engine = FakeInferenceEngine()
    engine.set_faces([(8, 2, 2), (8, 20, 20)])
    detector = YuNetFaceDetector(engine, _config())
    faces = detector.detect(blank_frame(640, 480))
    assert len(faces) == 2


def test_input_size_is_respected() -> None:
    engine = FakeInferenceEngine(input_width=256, input_height=256)
    engine.set_outputs(empty_yunet_outputs(256, 256))
    detector = YuNetFaceDetector(engine, _config(input_width=256, input_height=256, max_faces=4))
    detector.detect(blank_frame(800, 600))
    assert engine.last_input_shape == (1, 3, 256, 256)


def test_fixed_model_shape_mismatch_is_rejected() -> None:
    engine = FakeInferenceEngine(input_width=640, input_height=640)
    with pytest.raises(ModelLoadError, match="640x640"):
        YuNetFaceDetector(engine, _config(input_width=320, input_height=320))


def test_inference_exception_is_not_swallowed() -> None:
    engine = FakeInferenceEngine(fail_run=True)
    detector = YuNetFaceDetector(engine, _config())
    with pytest.raises(InferenceError, match="synthetic inference failure"):
        detector.detect(blank_frame(64, 48))


def test_threshold_and_max_faces_come_from_config() -> None:
    engine = FakeInferenceEngine()
    engine.set_faces([(8, 2, 2), (8, 20, 20)])
    detector = YuNetFaceDetector(engine, _config(max_faces=1, confidence_threshold=0.9))
    faces = detector.detect(blank_frame(320, 320))
    assert len(faces) == 1
    assert detector.config.confidence_threshold == 0.9
    assert detector.config.max_faces == 1
