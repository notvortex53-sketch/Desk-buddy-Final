"""Restricted Windows connector for Desk Buddy.

This agent deliberately supports only status reporting and opening validated
HTTP(S) URLs. It never executes shell commands, scripts, or arbitrary programs.
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit
import webbrowser


SERVICE_NAME = "Desk Buddy Windows Agent"
CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "DeskBuddy"
CONFIG_PATH = CONFIG_DIR / "agent.json"
MAX_BACKOFF_SECONDS = 60


class AgentActionError(ValueError):
    pass


def validate_gateway_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "wss" or not parsed.hostname or parsed.query or parsed.fragment:
        raise ValueError("Gateway URL must be a public wss:// URL without a query string or fragment.")
    path = parsed.path.rstrip("/")
    if path != "/ws/device":
        raise ValueError("Gateway URL must end with /ws/device.")
    return value.rstrip("/")


def validate_open_url(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048 or any(ord(char) < 32 for char in value):
        raise AgentActionError("The URL is invalid.")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise AgentActionError("Only credential-free HTTP(S) URLs are allowed.")
    return value


def execute_action(action: object) -> str:
    if not isinstance(action, dict):
        raise AgentActionError("The task action is invalid.")
    if action.get("authorization") != {"mode": "ethical", "owner_confirmed": True}:
        raise AgentActionError("Ethical Mode authorization is required for Windows actions.")
    name = action.get("name")
    args = action.get("args")
    if not isinstance(args, dict):
        raise AgentActionError("The task arguments are invalid.")
    if name == "get_status" and not args:
        return "Windows agent is connected and ready."
    if name == "open_url" and set(args) == {"url"}:
        url = validate_open_url(args["url"])
        if not webbrowser.open(url, new=2):
            raise AgentActionError("Windows could not open the requested URL.")
        return "Opened the requested URL in the default browser."
    raise AgentActionError("This Windows agent action is not allowed.")


def load_config() -> dict:
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(config.get("device_id"), str):
            raise ValueError
        config["gateway_url"] = validate_gateway_url(config["gateway_url"])
        return config
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        raise RuntimeError("The agent is not registered. Run the register command first.") from exc


def get_device_token(device_id: str) -> str:
    import keyring
    token = keyring.get_password(SERVICE_NAME, device_id)
    if not token:
        raise RuntimeError("The Windows Credential Manager device credential is missing. Register the agent again.")
    return token


def register_agent(device_id: str, device_token: str, gateway_url: str) -> None:
    if not device_id or not device_token:
        raise ValueError("A device ID and device token are required.")
    import keyring
    gateway_url = validate_gateway_url(gateway_url)
    keyring.set_password(SERVICE_NAME, device_id, device_token)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"device_id": device_id, "gateway_url": gateway_url}), encoding="utf-8")


def run_agent() -> None:
    import websocket
    config = load_config()
    backoff = 1
    while True:
        ws = None
        try:
            token = get_device_token(config["device_id"])
            ws = websocket.create_connection(config["gateway_url"], timeout=15)
            ws.send(json.dumps({"type": "auth", "device_id": config["device_id"], "token": token}))
            authenticated = json.loads(ws.recv())
            if authenticated.get("type") != "authenticated":
                raise RuntimeError("The gateway did not authenticate this agent.")
            heartbeat = authenticated.get("heartbeat_seconds")
            if not isinstance(heartbeat, int) or heartbeat <= 0:
                raise RuntimeError("The gateway returned an invalid heartbeat interval.")
            backoff = 1
            next_heartbeat = time.monotonic() + heartbeat
            while True:
                ws.settimeout(max(0.1, next_heartbeat - time.monotonic()))
                try:
                    raw_message = ws.recv()
                except websocket.WebSocketTimeoutException:
                    ws.send(json.dumps({"type": "ping"}))
                    next_heartbeat = time.monotonic() + heartbeat
                    continue
                if not raw_message:
                    raise RuntimeError("The gateway closed the connection.")
                message = json.loads(raw_message)
                if message.get("type") != "task":
                    continue
                task_id = message.get("task_id")
                if not isinstance(task_id, str):
                    continue
                try:
                    result = execute_action(message.get("action"))
                    payload = {"type": "task_result", "task_id": task_id, "ok": True, "result": result}
                except AgentActionError as exc:
                    payload = {"type": "task_result", "task_id": task_id, "ok": False, "result": str(exc)}
                ws.send(json.dumps(payload))
        except KeyboardInterrupt:
            return
        except Exception as exc:
            print(f"Desk Buddy agent disconnected: {exc}. Retrying in {backoff}s.", file=sys.stderr)
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
        finally:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Desk Buddy's restricted Windows agent")
    commands = parser.add_subparsers(dest="command", required=True)
    register = commands.add_parser("register", help="Save a paired device credential to Windows Credential Manager")
    register.add_argument("--device-id", required=True)
    register.add_argument("--device-token", required=True)
    register.add_argument("--gateway-url", required=True, help="wss://<host>/ws/device")
    commands.add_parser("run", help="Connect the registered agent to Desk Buddy")
    args = parser.parse_args()
    if args.command == "register":
        register_agent(args.device_id, args.device_token, args.gateway_url)
        print("Desk Buddy Windows agent registered. Run `run` to connect.")
    else:
        run_agent()


if __name__ == "__main__":
    main()
