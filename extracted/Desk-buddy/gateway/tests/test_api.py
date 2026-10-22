from fastapi.testclient import TestClient
from app.main import app


def test_root_and_health_are_available():
    with TestClient(app) as client:
        root = client.get("/")
        health = client.get("/health")
    assert root.status_code == 200
    assert root.json()["name"] == "Desk Buddy Gateway"
    assert health.status_code == 200
    assert health.json()["service"] == "desk-buddy-gateway"


def test_private_routes_are_present_in_openapi():
    schema = app.openapi()
    assert "/api/pair/start" in schema["paths"]
    assert "/api/pair/verify" in schema["paths"]
    assert "/api/devices" in schema["paths"]
    assert "/api/tasks" in schema["paths"]
    assert "/api/chat" in schema["paths"]
    assert "/api/devices/{device_id}/renew-credential" in schema["paths"]


def test_windows_portal_is_available():
    with TestClient(app) as client:
        response = client.get("/portal/windows")
    assert response.status_code == 200
    assert "Windows Agent Connection" in response.text
