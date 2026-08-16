"""ONNX Runtime inference engine. Session objects stay inside this module."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from app.core.logging import get_logger
from app.vision.exceptions import InferenceError, InferenceProviderError, ModelLoadError

logger = get_logger("app.vision")

CPU_PROVIDER = "CPUExecutionProvider"


class InferenceEngine(Protocol):
    """Minimal inference surface. Callers never receive a runtime session."""

    @property
    def input_name(self) -> str: ...

    @property
    def input_shape(self) -> tuple[int | None, ...]: ...

    @property
    def output_names(self) -> list[str]: ...

    @property
    def providers(self) -> list[str]: ...

    def run(self, inputs: dict[str, NDArray[np.float32]]) -> dict[str, NDArray[np.float32]]: ...


class OnnxRuntimeEngine:
    """ONNX Runtime engine pinned to CPUExecutionProvider."""

    def __init__(
        self,
        model_path: Path,
        *,
        intra_op_num_threads: int = 2,
        inter_op_num_threads: int = 1,
    ) -> None:
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise ModelLoadError("onnxruntime is not installed") from exc

        available = list(ort.get_available_providers())
        if CPU_PROVIDER not in available:
            raise InferenceProviderError(
                f"{CPU_PROVIDER} is not available. Available providers: {available}"
            )

        options = ort.SessionOptions()
        options.intra_op_num_threads = intra_op_num_threads
        options.inter_op_num_threads = inter_op_num_threads
        try:
            session = ort.InferenceSession(
                str(model_path),
                sess_options=options,
                providers=[CPU_PROVIDER],
            )
        except Exception as exc:
            raise ModelLoadError(f"Failed to load ONNX model: {model_path}") from exc

        active = list(session.get_providers())
        if not active or active[0] != CPU_PROVIDER:
            raise InferenceProviderError(
                f"Expected {CPU_PROVIDER} as the active provider, got {active}"
            )

        inputs = session.get_inputs()
        if not inputs:
            raise ModelLoadError(f"ONNX model has no inputs: {model_path}")
        outputs = session.get_outputs()
        if not outputs:
            raise ModelLoadError(f"ONNX model has no outputs: {model_path}")

        self._session = session
        self._lock = threading.Lock()
        self._input_name = str(inputs[0].name)
        self._input_shape = _normalize_shape(inputs[0].shape)
        self._output_names = [str(item.name) for item in outputs]
        self._providers = active
        logger.info(
            "ONNX Runtime engine ready path=%s provider=%s input=%s shape=%s",
            model_path,
            CPU_PROVIDER,
            self._input_name,
            self._input_shape,
        )

    @property
    def input_name(self) -> str:
        return self._input_name

    @property
    def input_shape(self) -> tuple[int | None, ...]:
        return self._input_shape

    @property
    def output_names(self) -> list[str]:
        return list(self._output_names)

    @property
    def providers(self) -> list[str]:
        return list(self._providers)

    def run(self, inputs: dict[str, NDArray[np.float32]]) -> dict[str, NDArray[np.float32]]:
        try:
            with self._lock:
                raw = self._session.run(self._output_names, inputs)
        except Exception as exc:
            raise InferenceError("ONNX Runtime inference failed") from exc
        result: dict[str, NDArray[np.float32]] = {}
        for name, value in zip(self._output_names, raw, strict=True):
            result[name] = np.asarray(value, dtype=np.float32)
        return result


def _normalize_shape(shape: object) -> tuple[int | None, ...]:
    dims: list[int | None] = []
    if not isinstance(shape, list | tuple):
        raise ModelLoadError(f"Unexpected ONNX input shape: {shape!r}")
    for dim in shape:
        if dim is None:
            dims.append(None)
            continue
        if isinstance(dim, str):
            dims.append(None)
            continue
        try:
            value = int(dim)
        except (TypeError, ValueError) as exc:
            raise ModelLoadError(f"Unexpected ONNX input dimension: {dim!r}") from exc
        dims.append(None if value <= 0 else value)
    return tuple(dims)
