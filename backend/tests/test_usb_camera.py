from __future__ import annotations

import time
from collections.abc import Iterator

import numpy as np
import pytest
from numpy.typing import NDArray

from app.cameras.exceptions import CameraNotAvailableError
from app.cameras.types import CameraConfig, CameraState
from app.cameras.usb import UsbCameraSource, VideoCaptureLike


class _FakeCapture:
    def __init__(self, *, opened: bool = True, image: NDArray[np.uint8] | None = None) -> None:
        self._opened = opened
        self.released = False
        self.image = image if image is not None else np.zeros((48, 64, 3), dtype=np.uint8)
        self.props: dict[int, float] = {3: 64.0, 4: 48.0, 5: 15.0}

    def isOpened(self) -> bool:  # noqa: N802
        return self._opened

    def read(self) -> tuple[bool, NDArray[np.uint8] | None]:
        if not self._opened:
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


def _config() -> CameraConfig:
    return CameraConfig(camera_id="usb-0", name="USB", device_index=0, width=64, height=48, fps=15)


@pytest.fixture
def usb_source() -> Iterator[UsbCameraSource]:
    capture = _FakeCapture()

    def opener(_index: int, _api: int) -> VideoCaptureLike:
        return capture

    source = UsbCameraSource(_config(), opener=opener)
    try:
        yield source
    finally:
        source.close()


def test_usb_open_start_read_stop_close(usb_source: UsbCameraSource) -> None:
    usb_source.open()
    assert usb_source.is_open()
    usb_source.start()
    assert usb_source.is_running()
    frame = None
    for _ in range(100):
        frame = usb_source.read()
        if frame is not None:
            break
        time.sleep(0.01)
    assert frame is not None
    assert frame.width == 64
    assert frame.height == 48
    assert frame.data.shape[2] == 3
    usb_source.stop()
    assert usb_source.get_status().state is CameraState.STOPPED
    usb_source.close()
    assert usb_source.get_status().state is CameraState.CLOSED
    assert not usb_source.is_open()


def test_usb_unavailable() -> None:
    def opener(_index: int, _api: int) -> VideoCaptureLike:
        return _FakeCapture(opened=False)

    source = UsbCameraSource(_config(), opener=opener)
    with pytest.raises(CameraNotAvailableError):
        source.open()
    assert source.get_status().state is CameraState.ERROR
    source.close()
    assert source.get_status().state is CameraState.CLOSED
