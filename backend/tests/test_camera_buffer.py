from __future__ import annotations

from datetime import UTC, datetime

import numpy as np

from app.cameras.buffer import LatestFrameSlot
from app.cameras.types import Frame


def test_latest_slot_replaces_stale_frame() -> None:
    slot = LatestFrameSlot()
    first = Frame(np.zeros((2, 2, 3), dtype=np.uint8), datetime.now(UTC), 2, 2)
    second = Frame(np.ones((2, 2, 3), dtype=np.uint8), datetime.now(UTC), 2, 2)
    slot.put(first)
    slot.put(second)
    got = slot.get()
    assert got is second
    slot.clear()
    assert slot.get() is None
