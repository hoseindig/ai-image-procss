from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_unhandled_error_hides_details_when_debug_disabled(settings: Settings) -> None:
    safe_settings = settings.model_copy(update={"debug": False})
    application = create_app(safe_settings)

    @application.get("/__boom")
    def boom() -> None:
        raise RuntimeError("secret internals")

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/__boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "Internal server error"
    assert "details" not in body["error"]
    assert "secret internals" not in response.text
    assert "Traceback" not in response.text


def test_unhandled_error_includes_details_when_debug_enabled(settings: Settings) -> None:
    application = create_app(settings)

    @application.get("/__boom")
    def boom() -> None:
        raise RuntimeError("secret internals")

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/__boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["details"] == "secret internals"
    assert "Traceback" not in response.text
