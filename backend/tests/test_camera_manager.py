from __future__ import annotations

import pytest

from app.cameras.exceptions import CameraInvalidStateError, CameraNotFoundError
from app.cameras.manager import CameraManager
from app.cameras.types import CameraConfig, CameraState
from tests.fake_camera import FakeCameraSource


def _config(camera_id: str = "cam-1") -> CameraConfig:
    return CameraConfig(camera_id=camera_id, name="Fake", width=32, height=24, fps=5)


def _manager() -> tuple[CameraManager, FakeCameraSource]:
    created: list[FakeCameraSource] = []

    def factory(config: CameraConfig) -> FakeCameraSource:
        source = FakeCameraSource(config)
        created.append(source)
        return source

    manager = CameraManager(source_factory=factory)
    manager.register(_config())
    return manager, created[0]


def test_manager_lifecycle() -> None:
    manager, source = _manager()
    assert manager.get_status("cam-1").state is CameraState.CLOSED
    manager.start("cam-1")
    assert source.is_running()
    frame = source.read()
    assert frame is not None
    assert frame.width == 32
    manager.stop("cam-1")
    assert source.get_status().state is CameraState.STOPPED
    manager.close("cam-1")
    assert source.get_status().state is CameraState.CLOSED
    manager.shutdown()


def test_manager_unknown_camera() -> None:
    manager, _source = _manager()
    with pytest.raises(CameraNotFoundError):
        manager.start("missing")


def test_manager_duplicate_register() -> None:
    manager, _source = _manager()
    with pytest.raises(CameraInvalidStateError):
        manager.register(_config())


def test_manager_shutdown_closes_running_camera() -> None:
    manager, source = _manager()
    manager.start("cam-1")
    manager.shutdown()
    assert source.get_status().state is CameraState.CLOSED
    assert source.close_count == 1


def test_manager_summary() -> None:
    manager, _source = _manager()
    available, running = manager.summary()
    assert available is True
    assert running is False
    manager.start("cam-1")
    available, running = manager.summary()
    assert running is True
    manager.shutdown()
