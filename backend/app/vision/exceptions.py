"""Domain errors for the vision subsystem. API handlers map these to HTTP."""


class VisionError(Exception):
    """Base vision error. Safe to convert to an API response."""

    def __init__(self, message: str, *, code: str = "vision_error") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ModelNotFoundError(VisionError):
    def __init__(self, path: str, *, model_name: str = "Model") -> None:
        super().__init__(f"{model_name} model not found:\n{path}", code="model_not_found")
        self.path = path
        self.model_name = model_name


class ModelLoadError(VisionError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="model_load_failed")


class InferenceProviderError(VisionError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="inference_provider_failed")


class InferenceError(VisionError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="inference_failed")
