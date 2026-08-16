from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import PROJECT_ROOT
from app.vision.engine import CPU_PROVIDER, OnnxRuntimeEngine
from app.vision.exceptions import ModelLoadError
from app.vision.factory import create_face_detector
from tests.helpers import IsolatedSettings
from tests.yunet_helpers import blank_frame

MODEL_PATH = PROJECT_ROOT / "models" / "face" / "yunet" / "2023mar.onnx"

requires_yunet = pytest.mark.skipif(
    not MODEL_PATH.is_file(),
    reason="YuNet model is not installed; run python scripts/download_models.py",
)


@requires_yunet
def test_real_yunet_loads_cpu_provider() -> None:
    engine = OnnxRuntimeEngine(MODEL_PATH)
    assert engine.providers[0] == CPU_PROVIDER
    assert engine.input_shape[2] == 640
    assert engine.input_shape[3] == 640


@requires_yunet
def test_real_yunet_detects_no_face_on_blank_image() -> None:
    settings = IsolatedSettings(
        face_detection_enabled=True,
        face_detection_model_path=str(MODEL_PATH),
        face_detection_input_width=640,
        face_detection_input_height=640,
    )
    detector = create_face_detector(settings)
    faces = detector.detect(blank_frame(640, 480, fill=0))
    assert faces == []
    assert detector.provider == CPU_PROVIDER


@requires_yunet
def test_real_yunet_rejects_wrong_configured_input_size() -> None:
    settings = IsolatedSettings(
        face_detection_enabled=True,
        face_detection_model_path=str(MODEL_PATH),
        face_detection_input_width=320,
        face_detection_input_height=320,
    )
    with pytest.raises(ModelLoadError, match="640x640"):
        create_face_detector(settings)


def test_fixture_readme_exists() -> None:
    readme = Path(__file__).resolve().parent / "fixtures" / "README.md"
    assert readme.is_file()
