from fastapi import status
from fastapi.testclient import TestClient

from app.api.v1 import health
from app.main import app

client = TestClient(app)


def _patch_services(monkeypatch, services: dict[str, str]) -> None:
    monkeypatch.setattr(health, "collect_health", lambda: services)


def test_health_returns_healthy_when_services_are_up(monkeypatch) -> None:
    _patch_services(monkeypatch, {"database": "up", "redis": "up", "object_storage": "up"})

    response = client.get("/api/v1/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "healthy",
        "services": {"database": "up", "redis": "up", "object_storage": "up"},
    }


def test_health_returns_unhealthy_when_database_is_down(monkeypatch) -> None:
    _patch_services(monkeypatch, {"database": "down", "redis": "up", "object_storage": "up"})

    response = client.get("/api/v1/health")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["status"] == "unhealthy"
    assert response.json()["services"]["database"] == "down"


def test_health_returns_unhealthy_when_redis_is_down(monkeypatch) -> None:
    _patch_services(monkeypatch, {"database": "up", "redis": "down", "object_storage": "up"})

    response = client.get("/api/v1/health")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["status"] == "unhealthy"
    assert response.json()["services"]["redis"] == "down"


def test_health_returns_unhealthy_when_object_storage_is_down(monkeypatch) -> None:
    _patch_services(monkeypatch, {"database": "up", "redis": "up", "object_storage": "down"})

    response = client.get("/api/v1/health")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["status"] == "unhealthy"
    assert response.json()["services"]["object_storage"] == "down"


def test_health_response_does_not_include_secret_values(monkeypatch) -> None:
    _patch_services(monkeypatch, {"database": "up", "redis": "up", "object_storage": "up"})

    response = client.get("/api/v1/health")
    body = response.text

    assert "securedocs_password" not in body
    assert "minioadmin" not in body
    assert "change-me" not in body
    assert "postgresql+psycopg" not in body
