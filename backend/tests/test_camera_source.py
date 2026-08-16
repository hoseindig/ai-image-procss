from __future__ import annotations

import pytest

from app.cameras.exceptions import (
    CameraAlreadyRunningError,
    CameraInvalidStateError,
    CameraNotAvailableError,
    CameraOpenError,
    CameraReadError,
)
from app.cameras.types import CameraConfig, CameraState
from tests.fake_camera import FakeCameraSource


def _config() -> CameraConfig:
    return CameraConfig(
        camera_id="cam-1",
        name="Fake",
        device_index=0,
        width=64,
        height=48,
        fps=10,
    )


def test_lifecycle_closed_open_running_stopped_closed() -> None:
    source = FakeCameraSource(_config())
    assert source.get_status().state is CameraState.CLOSED
    source.open()
    assert source.get_status().state is CameraState.OPEN
    source.start()
    assert source.get_status().state is CameraState.RUNNING
    frame = source.read()
    assert frame is not None
    assert frame.width == 64
    assert frame.height == 48
    assert frame.data.shape == (48, 64, 3)
    assert frame.timestamp.tzinfo is not None
    source.stop()
    assert source.get_status().state is CameraState.STOPPED
    source.close()
    assert source.get_status().state is CameraState.CLOSED
    assert source.close_count == 1


def test_start_before_open_fails() -> None:
    source = FakeCameraSource(_config())
    with pytest.raises(CameraInvalidStateError):
        source.start()


def test_double_start_fails() -> None:
    source = FakeCameraSource(_config())
    source.open()
    source.start()
    with pytest.raises(CameraAlreadyRunningError):
        source.start()
    source.close()


def test_double_stop_fails() -> None:
    source = FakeCameraSource(_config())
    source.open()
    source.start()
    source.stop()
    with pytest.raises(CameraInvalidStateError):
        source.stop()
    source.close()


def test_read_before_open_fails() -> None:
    source = FakeCameraSource(_config())
    with pytest.raises(CameraInvalidStateError):
        source.read()


def test_read_after_close_fails() -> None:
    source = FakeCameraSource(_config())
    source.open()
    source.start()
    source.close()
    with pytest.raises(CameraInvalidStateError):
        source.read()


def test_unavailable_camera() -> None:
    source = FakeCameraSource(_config(), unavailable=True)
    with pytest.raises(CameraNotAvailableError):
        source.open()
    assert source.get_status().state is CameraState.ERROR
    source.close()
    assert source.get_status().state is CameraState.CLOSED
    assert source.close_count == 1


def test_open_failure_cleans_up() -> None:
    source = FakeCameraSource(_config(), fail_open=True)
    with pytest.raises(CameraOpenError):
        source.open()
    source.close()
    assert source.close_count == 1
    assert source.get_status().state is CameraState.CLOSED


def test_read_failure() -> None:
    source = FakeCameraSource(_config(), fail_read=True)
    source.open()
    source.start()
    with pytest.raises(CameraReadError):
        source.read()
    source.close()
    assert source.close_count == 1
