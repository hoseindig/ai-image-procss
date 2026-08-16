"""Phase 11: camera failure recovery, worker lifecycle, USB read failures."""

from __future__ import annotations

import time
from collections.abc import Iterator

import numpy as np
import pytest
from numpy.typing import NDArray

from app.cameras.exceptions import CameraInvalidStateError, CameraReadError
from app.cameras.manager import CameraManager
from app.cameras.types import CameraConfig, CameraState
from app.cameras.usb import UsbCameraSource, VideoCaptureLike
from app.services.camera import CameraService
from app.vision.runtime import DetectionRuntime
from app.vision.worker import DetectionWorker
from tests.fake_camera import FakeCameraSource
from tests.fake_vision import FakeFaceDetector
from tests.helpers import IsolatedSettings
from tests.yunet_helpers import sample_face


class _FailingCapture:
    """Capture that succeeds on open verify, then fails reads."""

    def __init__(self, *, fail_after: int = 1) -> None:
        self._opened = True
        self.released = False
        self._reads = 0
        self._fail_after = fail_after
        self.image: NDArray[np.uint8] = np.zeros((48, 64, 3), dtype=np.uint8)
        self.props: dict[int, float] = {3: 64.0, 4: 48.0, 5: 15.0}

    def isOpened(self) -> bool:  # noqa: N802
        return self._opened

    def read(self) -> tuple[bool, NDArray[np.uint8] | None]:
        self._reads += 1
        if self._reads > self._fail_after:
            return False, None
        return True, self.image

    def release(self) -> None:
        self.released = True
        self._opened = False

    def set(self, prop_id: int, value: float) -> bool:
        self.props[prop_id] = value
        return True

    def get(self, prop_id: int) -> float:
        return self.props.get(prop_id, 0.0)


def _usb_config(**kwargs: object) -> CameraConfig:
    base: dict[str, object] = {
        "camera_id": "usb-0",
        "name": "USB",
        "device_index": 0,
        "width": 64,
        "height": 48,
        "fps": 15,
        "max_consecutive_read_failures": 3,
    }
    base.update(kwargs)
    return CameraConfig(**base)  # type: ignore[arg-type]


@pytest.fixture
def fail_read_source() -> Iterator[UsbCameraSource]:
    capture = _FailingCapture(fail_after=1)

    def opener(_index: int, _api: int) -> VideoCaptureLike:
        return capture

    source = UsbCameraSource(_usb_config(), opener=opener)
    try:
        yield source
    finally:
        source.close()


def test_usb_consecutive_read_failures_enter_error(fail_read_source: UsbCameraSource) -> None:
    source = fail_read_source
    source.open()
    source.start()
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if source.get_status().state is CameraState.ERROR:
            break
        time.sleep(0.02)
    assert source.get_status().state is CameraState.ERROR
    assert source.get_status().error == "Camera stopped returning frames"
    with pytest.raises(CameraReadError):
        source.read()
    source.stop()
    assert source.get_status().state is CameraState.ERROR
    source.close()
    assert source.get_status().state is CameraState.CLOSED


def test_camera_service_recovers_from_error() -> None:
    created: list[FakeCameraSource] = []

    def factory(config: CameraConfig) -> FakeCameraSource:
        source = FakeCameraSource(config, fail_read=True)
        created.append(source)
        return source

    manager = CameraManager(source_factory=factory)
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=32, height=24, fps=5))
    settings = IsolatedSettings(
        app_env="test",
        face_detection_enabled=False,
        face_embedding_enabled=False,
        camera_recover_on_start=True,
    )
    runtime = DetectionRuntime(None, settings, manager)
    service = CameraService(manager, runtime, settings)

    service.start_camera("cam-1")
    with pytest.raises(CameraReadError):
        created[0].read()
    assert created[0].get_status().state is CameraState.ERROR

    # Swap behavior: next open works (same Fake instance after close→open).
    created[0]._fail_read = False  # noqa: SLF001
    status = service.start_camera("cam-1")
    assert status.state is CameraState.RUNNING
    service.stop_camera("cam-1")
    assert created[0].get_status().state is CameraState.CLOSED


def test_camera_service_stop_from_error() -> None:
    manager = CameraManager(source_factory=lambda config: FakeCameraSource(config, fail_read=True))
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=32, height=24, fps=5))
    settings = IsolatedSettings(app_env="test", face_detection_enabled=False)
    runtime = DetectionRuntime(None, settings, manager)
    service = CameraService(manager, runtime, settings)
    service.start_camera("cam-1")
    source = manager.get_source("cam-1")
    with pytest.raises(CameraReadError):
        source.read()
    status = service.stop_camera("cam-1")
    assert status.state is CameraState.CLOSED


def test_manager_start_stop_start_stop_cycle() -> None:
    created: list[FakeCameraSource] = []

    def factory(config: CameraConfig) -> FakeCameraSource:
        source = FakeCameraSource(config)
        created.append(source)
        return source

    manager = CameraManager(source_factory=factory)
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=32, height=24, fps=5))
    for _ in range(3):
        manager.start("cam-1")
        assert created[0].is_running()
        manager.stop("cam-1")
        assert created[0].get_status().state is CameraState.STOPPED
    manager.close("cam-1")
    manager.shutdown()


def test_worker_exits_cleanly_on_camera_read_error() -> None:
    source = FakeCameraSource(
        CameraConfig(camera_id="cam-1", name="Fake", width=64, height=48, fps=10),
        fail_read=True,
    )
    source.open()
    source.start()
    worker = DetectionWorker("cam-1", source.read, FakeFaceDetector(), interval_ms=5)
    try:
        worker.start()
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and worker.is_running():
            time.sleep(0.02)
        assert worker.is_running() is False
    finally:
        worker.stop()
        source.close()


def test_worker_repeated_start_stop() -> None:
    source = FakeCameraSource(
        CameraConfig(camera_id="cam-1", name="Fake", width=64, height=48, fps=10)
    )
    source.open()
    source.start()
    detector = FakeFaceDetector([sample_face(x=4, y=4, width=16, height=16)])
    worker = DetectionWorker("cam-1", source.read, detector, interval_ms=10)
    try:
        for _ in range(3):
            worker.start()
            assert worker.is_running()
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and worker.latest() is None:
                time.sleep(0.01)
            worker.stop()
            assert worker.is_running() is False
    finally:
        source.close()


def test_worker_shutdown_while_processing() -> None:
    source = FakeCameraSource(
        CameraConfig(camera_id="cam-1", name="Fake", width=64, height=48, fps=10)
    )
    source.open()
    source.start()
    worker = DetectionWorker(
        "cam-1",
        source.read,
        FakeFaceDetector([sample_face(x=4, y=4, width=16, height=16)]),
        interval_ms=5,
    )
    worker.start()
    time.sleep(0.05)
    worker.stop()
    assert worker.is_running() is False
    source.close()


def test_recover_disabled_rejects_error_start() -> None:
    manager = CameraManager(source_factory=lambda config: FakeCameraSource(config, fail_read=True))
    manager.register(CameraConfig(camera_id="cam-1", name="Fake", width=32, height=24, fps=5))
    settings = IsolatedSettings(
        app_env="test",
        face_detection_enabled=False,
        camera_recover_on_start=False,
    )
    runtime = DetectionRuntime(None, settings, manager)
    service = CameraService(manager, runtime, settings)
    service.start_camera("cam-1")
    with pytest.raises(CameraReadError):
        manager.get_source("cam-1").read()
    with pytest.raises(CameraInvalidStateError):
        service.start_camera("cam-1")
