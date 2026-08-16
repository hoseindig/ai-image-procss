"""Vision HTTP error mapping."""

from __future__ import annotations

from app.vision.exceptions import (
    InferenceError,
    InferenceProviderError,
    ModelLoadError,
    ModelNotFoundError,
    VisionError,
)


def vision_error_http_status(exc: VisionError) -> int:
    if isinstance(exc, ModelNotFoundError | ModelLoadError | InferenceProviderError):
        return 503
    if isinstance(exc, InferenceError):
        return 503
    return 400
