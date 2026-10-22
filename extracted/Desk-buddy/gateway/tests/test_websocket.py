from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.config import settings
from app.db import Base, SessionLocal, engine
from app import main
from app.main import app, connected_devices
from app.models import Device, UserSession
from app.security import hash_device_token, hash_session_token


DEVICE_ID = "esp32c3-test-device"
DEVICE_TOKEN = "dbd_test-device-token"


def setup_function():
    settings.device_token_pepper = "test-pepper-that-is-long-enough-for-the-security-check"
    settings.device_heartbeat_seconds = 25
    settings.windows_reauthentication_seconds = 3600
    settings.android_reauthentication_seconds = 3600
    settings.ethical_mode_required = True
    connected_devices.clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add(Device(
        id=DEVICE_ID,
        email="owner@example.com",
        device_type="esp32c3",
        label="Test ESP32-C3",
        token_hash=hash_device_token(DEVICE_TOKEN),
        revoked=False,
    ))
    db.commit()
    db.close()


def teardown_function():
    connected_devices.clear()
    Base.metadata.drop_all(bind=engine)


def test_device_websocket_authenticates_and_answers_heartbeat():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/device") as websocket:
            websocket.send_json({"type": "auth", "device_id": DEVICE_ID, "token": DEVICE_TOKEN})
            authenticated = websocket.receive_json()
            assert authenticated == {
                "type": "authenticated",
                "device_id": DEVICE_ID,
                "heartbeat_seconds": 25,
            }
            assert DEVICE_ID in connected_devices

            websocket.send_json({"type": "ping"})
            pong = websocket.receive_json()
            assert pong["type"] == "pong"
            assert "time" in pong


def test_device_websocket_rejects_invalid_credential():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/device") as websocket:
            websocket.send_json({"type": "auth", "device_id": DEVICE_ID, "token": "wrong-token"})
            message = websocket.receive()
    assert message["type"] == "websocket.close"
    assert message["code"] == 4401


def test_windows_agent_is_told_to_reauthenticate_hourly():
    db = SessionLocal()
    device = db.get(Device, DEVICE_ID)
    device.device_type = "windows"
    db.commit()
    db.close()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/device") as websocket:
            websocket.send_json({"type": "auth", "device_id": DEVICE_ID, "token": DEVICE_TOKEN})
            authenticated = websocket.receive_json()
    assert authenticated["reauthenticate_after_seconds"] == 3600


def test_android_agent_is_told_to_reauthenticate_hourly():
    db = SessionLocal()
    device = db.get(Device, DEVICE_ID)
    device.device_type = "android"
    db.commit()
    db.close()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/device") as websocket:
            websocket.send_json({"type": "auth", "device_id": DEVICE_ID, "token": DEVICE_TOKEN})
            authenticated = websocket.receive_json()
    assert authenticated["reauthenticate_after_seconds"] == 3600


def test_windows_task_requires_and_carries_ethical_mode_authorization(monkeypatch):
    session_token = "dbs_test-owner-session"
    db = SessionLocal()
    device = db.get(Device, DEVICE_ID)
    device.device_type = "windows"
    db.add(UserSession(
        id="test-owner-session",
        email="owner@example.com",
        token_hash=hash_session_token(session_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked=False,
    ))
    db.commit()
    db.close()
    headers = {"Authorization": f"Bearer {session_token}"}
    monkeypatch.setattr(main, "review_ethical_task", lambda action: {"allow": True, "risk": "low", "reason": "Allowlisted status request.", "requires_confirmation": False})
    with TestClient(app) as client:
        with client.websocket_connect("/ws/device") as websocket:
            websocket.send_json({"type": "auth", "device_id": DEVICE_ID, "token": DEVICE_TOKEN})
            websocket.receive_json()
            denied = client.post("/api/tasks", headers=headers, json={"device_id": DEVICE_ID, "action": "get_status"})
            assert denied.status_code == 403
            approved = client.post("/api/tasks", headers=headers, json={
                "device_id": DEVICE_ID,
                "action": "get_status",
                "ethical_mode_approved": True,
            })
            assert approved.status_code == 200
            task = websocket.receive_json()
    assert task["action"]["authorization"] == {
        "mode": "ethical",
        "owner_confirmed": True,
        "review_model": main.settings.ethical_model,
        "risk": "low",
        "reason": "Allowlisted status request.",
    }


def test_owner_can_renew_windows_credential_once():
    session_token = "dbs_test-renew-session"
    db = SessionLocal()
    device = db.get(Device, DEVICE_ID)
    device.device_type = "windows"
    db.add(UserSession(
        id="test-renew-session",
        email="owner@example.com",
        token_hash=hash_session_token(session_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked=False,
    ))
    db.commit()
    db.close()
    with TestClient(app) as client:
        response = client.post(
            f"/api/devices/{DEVICE_ID}/renew-credential",
            headers={"Authorization": f"Bearer {session_token}"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["device_id"] == DEVICE_ID
    assert payload["device_token"].startswith("dbd_")
    assert payload["websocket_url"].endswith("/ws/device")
    assert payload["device_token"] in payload["connection_command"]
    assert response.headers["cache-control"] == "no-store"
    db = SessionLocal()
    renewed = db.get(Device, DEVICE_ID)
    assert renewed.token_hash == hash_device_token(payload["device_token"])
    db.close()


def test_device_websocket_returns_chat_response(monkeypatch):
    monkeypatch.setattr(main, "generate_chat_answer", lambda message: f"Reply: {message}")
    with TestClient(app) as client:
        with client.websocket_connect("/ws/device") as websocket:
            websocket.send_json({"type": "auth", "device_id": DEVICE_ID, "token": DEVICE_TOKEN})
            websocket.receive_json()
            websocket.send_json({"type": "chat", "request_id": "chat-1", "message": "Hello"})
            assert websocket.receive_json() == {
                "type": "chat_response",
                "request_id": "chat-1",
                "answer": "Reply: Hello",
                "model": settings.chat_model,
            }


def test_device_websocket_returns_safe_chat_provider_error(monkeypatch):
    def provider_failure(message):
        raise RuntimeError("provider details must not reach the device")

    monkeypatch.setattr(main, "generate_chat_answer", provider_failure)
    with TestClient(app) as client:
        with client.websocket_connect("/ws/device") as websocket:
            websocket.send_json({"type": "auth", "device_id": DEVICE_ID, "token": DEVICE_TOKEN})
            websocket.receive_json()
            websocket.send_json({"type": "chat", "request_id": "chat-2", "message": "Hello"})
            assert websocket.receive_json() == {
                "type": "chat_error",
                "request_id": "chat-2",
                "code": "model_request_failed",
                "message": "The chat provider could not complete the request. Please retry.",
            }
