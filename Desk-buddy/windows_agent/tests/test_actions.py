import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desk_buddy_agent import AgentActionError, execute_action, validate_gateway_url, validate_open_url


def test_gateway_url_must_be_the_secure_device_endpoint():
    assert validate_gateway_url("wss://desk-buddy.onrender.com/ws/device") == "wss://desk-buddy.onrender.com/ws/device"
    with pytest.raises(ValueError):
        validate_gateway_url("ws://desk-buddy.onrender.com/ws/device")


def test_open_url_rejects_non_web_and_credential_urls():
    with pytest.raises(AgentActionError):
        validate_open_url("file:///C:/Windows/System32/cmd.exe")
    with pytest.raises(AgentActionError):
        validate_open_url("https://user:password@example.com")


def test_agent_rejects_unsupported_actions():
    with pytest.raises(AgentActionError):
        execute_action({"name": "run_command", "args": {"command": "whoami"}})


def test_agent_rejects_actions_without_ethical_mode_authorization():
    with pytest.raises(AgentActionError, match="Ethical Mode"):
        execute_action({"name": "get_status", "args": {}})
