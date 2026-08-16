"""Event type enum. Extensible; only recognized/unknown_face are emitted in Phase 8."""

from __future__ import annotations

from enum import StrEnum


class EventType(StrEnum):
    RECOGNIZED = "recognized"
    UNKNOWN_FACE = "unknown_face"
    # Future-compatible (not emitted yet):
    TRACK_STARTED = "track_started"
    TRACK_LOST = "track_lost"
