"""Fake vision implementations for tests. No ONNX Runtime and no webcam."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from app.cameras.types import Frame
from app.vision.engine import CPU_PROVIDER
from app.vision.exceptions import InferenceError
from app.vision.types import FaceDetection
from tests.yunet_helpers import empty_yunet_outputs, yunet_outputs_with_faces


class FakeInferenceEngine:
    def __init__(
        self,
        *,
        input_name: str = "input",
        input_width: int = 320,
        input_height: int = 320,
        outputs: dict[str, NDArray[np.float32]] | None = None,
        providers: tuple[str, ...] = (CPU_PROVIDER,),
        fail_run: bool = False,
    ) -> None:
        self._input_name = input_name
        self._input_shape: tuple[int | None, ...] = (1, 3, input_height, input_width)
        self._outputs = (
            outputs if outputs is not None else empty_yunet_outputs(input_width, input_height)
        )
        self._providers = list(providers)
        self._output_names = list(self._outputs.keys())
        self.fail_run = fail_run
        self.last_input_shape: tuple[int, ...] | None = None
        self.run_count = 0

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

    def set_outputs(self, outputs: dict[str, NDArray[np.float32]]) -> None:
        self._outputs = outputs
        self._output_names = list(outputs.keys())

    def set_faces(self, faces: list[tuple[int, int, int]]) -> None:
        width = int(self._input_shape[3] or 320)
        height = int(self._input_shape[2] or 320)
        self.set_outputs(yunet_outputs_with_faces(width, height, faces))

    def run(self, inputs: dict[str, NDArray[np.float32]]) -> dict[str, NDArray[np.float32]]:
        self.run_count += 1
        blob = inputs[self._input_name]
        self.last_input_shape = tuple(int(dim) for dim in blob.shape)
        if self.fail_run:
            raise InferenceError("synthetic inference failure")
        return self._outputs


class FakeFaceDetector:
    provider = "test"

    def __init__(
        self,
        faces: list[FaceDetection] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.faces = list(faces or [])
        self.error = error
        self.calls = 0
        self.last_frame: Frame | None = None

    def detect(self, frame: Frame) -> list[FaceDetection]:
        self.calls += 1
        self.last_frame = frame
        if self.error is not None:
            raise self.error
        return list(self.faces)
