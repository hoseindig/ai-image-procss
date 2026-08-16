from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_when_features_disabled(client: TestClient) -> None:
    response = client.get("/api/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"]["ok"] is True
    assert body["models"]["ok"] is True
    assert body["camera_required_for_ready"] is False


def test_system_status_returns_ok(client: TestClient) -> None:
    response = client.get("/api/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert body["database"]["connected"] is True
    assert isinstance(body["python_version"], str)
    assert body["python_version"].startswith("3.13")
    assert body["uptime_seconds"] >= 0
    assert body["camera"]["available"] is True
    assert body["camera"]["running"] is False
    assert body["face_detection"]["enabled"] is False
    assert body["face_detection"]["model_loaded"] is False
    assert body["face_detection"]["provider"] is None
    assert body["face_detection"]["tracking_enabled"] is True
    assert body["face_detection"]["quality_enabled"] is True
    assert body["face_detection"]["alignment_enabled"] is True
    assert body["face_detection"]["embedding_enabled"] is False
    assert body["face_detection"]["embedding_provider"] is None
    assert body["face_detection"]["recognition_enabled"] is False
    assert body["face_detection"]["recognition_threshold"] is None
    assert body["face_detection"]["event_logging_enabled"] is False
    assert body["ready"] is True
    assert "database_url" not in body
    assert "DATABASE_URL" not in response.text
