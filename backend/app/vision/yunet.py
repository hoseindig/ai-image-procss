"""YuNet face detector. ONNX Runtime details stay behind InferenceEngine."""

from __future__ import annotations

from dataclasses import dataclass

from app.cameras.types import Frame
from app.core.logging import get_logger
from app.vision.decode import YUNET_OUTPUT_NAMES, RawFace, decode_yunet
from app.vision.engine import CPU_PROVIDER, InferenceEngine
from app.vision.exceptions import InferenceError, ModelLoadError
from app.vision.geometry import (
    CoordinateMapper,
    bgr_to_nchw_float,
    clip_detection,
    pad_bottom_right,
    padded_size,
    resize_bgr,
)
from app.vision.types import FaceDetection, FaceLandmarks

logger = get_logger("app.vision")


@dataclass(frozen=True)
class YuNetConfig:
    confidence_threshold: float
    nms_threshold: float
    input_width: int
    input_height: int
    max_faces: int


class YuNetFaceDetector:
    """FaceDetector implementation using OpenCV Zoo YuNet via ONNX Runtime CPU."""

    def __init__(self, engine: InferenceEngine, config: YuNetConfig) -> None:
        self._engine = engine
        self._config = _resolved_config(engine, config)
        _require_yunet_outputs(engine)
        logger.info(
            "YuNet detector ready provider=%s input=%sx%s confidence_threshold=%.3f "
            "nms_threshold=%.3f max_faces=%s",
            ", ".join(engine.providers),
            self._config.input_width,
            self._config.input_height,
            self._config.confidence_threshold,
            self._config.nms_threshold,
            self._config.max_faces,
        )

    @property
    def config(self) -> YuNetConfig:
        return self._config

    @property
    def provider(self) -> str:
        providers = self._engine.providers
        return providers[0] if providers else CPU_PROVIDER

    def detect(self, frame: Frame) -> list[FaceDetection]:
        if frame.data.ndim != 3 or frame.data.shape[2] != 3:
            raise InferenceError("Face detection requires an HxWx3 BGR frame")
        mapper = CoordinateMapper(
            original_width=frame.width,
            original_height=frame.height,
            input_width=self._config.input_width,
            input_height=self._config.input_height,
        )
        resized = resize_bgr(frame.data, self._config.input_width, self._config.input_height)
        pad_width, pad_height = padded_size(self._config.input_width, self._config.input_height)
        padded = pad_bottom_right(resized, pad_width, pad_height)
        blob = bgr_to_nchw_float(padded)
        outputs = self._engine.run({self._engine.input_name: blob})
        raw_faces = decode_yunet(
            outputs,
            pad_width=pad_width,
            pad_height=pad_height,
            score_threshold=self._config.confidence_threshold,
            nms_threshold=self._config.nms_threshold,
            max_faces=self._config.max_faces,
        )
        return [
            clip_detection(_to_detection(item, mapper), frame.width, frame.height)
            for item in raw_faces
        ]


def _resolved_config(engine: InferenceEngine, config: YuNetConfig) -> YuNetConfig:
    shape = engine.input_shape
    if len(shape) != 4:
        raise ModelLoadError(f"YuNet expected NCHW input, got shape {shape}")
    model_height, model_width = shape[2], shape[3]
    dynamic_h = model_height is None
    dynamic_w = model_width is None
    if dynamic_h or dynamic_w:
        return config
    if model_width != config.input_width or model_height != config.input_height:
        raise ModelLoadError(
            "YuNet model input is "
            f"{model_width}x{model_height}; configured FACE_DETECTION_INPUT_WIDTH/HEIGHT is "
            f"{config.input_width}x{config.input_height}. ONNX Runtime cannot reshape this "
            "fixed-size graph. Set the configured size to match the model "
            f"({model_width}x{model_height})."
        )
    return config


def _require_yunet_outputs(engine: InferenceEngine) -> None:
    available = set(engine.output_names)
    missing = [name for name in YUNET_OUTPUT_NAMES if name not in available]
    if missing:
        raise ModelLoadError(f"YuNet output tensors missing: {', '.join(missing)}")


def _to_detection(raw: RawFace, mapper: CoordinateMapper) -> FaceDetection:
    return FaceDetection(
        bounding_box=mapper.box(raw.x, raw.y, raw.width, raw.height),
        confidence=raw.confidence,
        landmarks=FaceLandmarks(
            left_eye=mapper.point(raw.left_eye_x, raw.left_eye_y),
            right_eye=mapper.point(raw.right_eye_x, raw.right_eye_y),
            nose=mapper.point(raw.nose_x, raw.nose_y),
            left_mouth=mapper.point(raw.left_mouth_x, raw.left_mouth_y),
            right_mouth=mapper.point(raw.right_mouth_x, raw.right_mouth_y),
        ),
    )
