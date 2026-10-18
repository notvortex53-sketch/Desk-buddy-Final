# Desk Buddy ESP32-C3 Mini — Phase 7

This firmware connects the ESP32-C3 Mini directly to the existing Render gateway using **WSS** and the protocol in `../gateway/docs/protocol.md`.

## Current features

- Direct TLS WebSocket to `wss://desk-buddy-485q.onrender.com/ws/device`
- Server certificate verification through the ESP32 Arduino core's built-in CA bundle (no insecure TLS mode)
- Device ID + persistent device token authentication in the first WebSocket message
- Gateway-provided heartbeat interval and ping/pong
- WebSocket reconnection with increasing retry interval
- Serial Monitor chat through the gateway's existing `chat` message contract
- Status query and safe `get_status` task result handling
- No arbitrary shell/command execution on the ESP32

## Important current backend limits

This firmware matches the backend currently in the uploaded ZIP. The gateway's WebSocket supports `auth`, `ping`, `status`, `chat`, and `task_result`; it does **not** currently accept audio, transcribe microphone input, or accept a device-originated `task_request` that routes a natural-language request to Windows. The existing owner `/api/tasks` route requires the owner's session token and explicit `ethical_mode_approved` for Windows. The ESP32 does not store that owner session token, and this firmware deliberately does not bypass that security boundary.

Therefore, this build proves direct secure ESP32-to-Render **text chat** using the Serial Monitor. To support “Buddy, open Notepad and type hello” by microphone, a later backend change must add authenticated speech-to-text and a server-side intent/approval workflow that dispatches only allow-listed tasks to the Windows agent. A microphone and its wiring must also be specified before audio capture can be implemented.

## Hardware / software requirements

- ESP32-C3 Mini / Super Mini
- Arduino IDE with **ESP32 Arduino core 3.0.4 or newer**
- Arduino Library Manager libraries:
  - `WebSockets` by Markus Sattler / Links2004 (`WebSocketsClient.h`)
  - `ArduinoJson` by Benoit Blanchon
- Render service deployed and healthy, with a working model configuration
- Device already paired in Desk Buddy as `device_type="esp32c3"`

The ESP32 core version requirement is intentional: the firmware uses the built-in TLS CA bundle so certificate checks remain enabled without hard-coding a short-lived leaf certificate. If the TLS connection fails, check NTP/time sync, internet access, core version, and Render status. Do **not** fix TLS errors by calling `setInsecure()`.

## Setup

1. Open `DeskBuddy_ESP32C3.ino` in Arduino IDE.
2. Copy `config.example.h` to `config.h` in the same sketch folder.
3. Set `WIFI_SSID` and `WIFI_PASSWORD`.
4. Pair the ESP32-C3 from the portal's email OTP flow as an `esp32c3` device. Save the returned `device_id` and `device_token`; enter them into `config.h`. The device token is persistent until revoked/rotated. Never publish it.
5. Select your ESP32-C3 board and correct USB/COM port. Set Serial Monitor to **115200 baud**.
6. Compile and upload. Wait for `Authenticated as ...` in Serial Monitor.
7. Type a message and press Enter. Use `/status` for status and `/help` for commands.

## Credential safety

- `config.h` is local-only and should never be committed.
- Do not put the token in the WebSocket URL, query string, logs, or screenshots.
- Revoke the device from the owner portal if the token is exposed or the board is lost.
- Pair/reissue credentials if a revoked device must be restored.

## Troubleshooting

- `4401` / invalid credential: check the device ID and token match the pairing response, and verify the device was not revoked.
- No model response: check `/health` for `model_configured`, Render logs, and the provider configuration.
- TLS errors: ensure ESP32 Arduino core >= 3.0.4, NTP time synchronization, and correct Render hostname. Certificate validation remains on.
- Repeated reconnects: Render may be sleeping/restarting, Wi-Fi may be weak, or the service may not be deployed.


## Gateway voice API added in Phase 8

The updated gateway ZIP now exposes `POST /api/device/voice` and `GET /api/device/voice/{audio_id}/audio`. This existing Phase 7 sketch does **not** yet capture or play audio; it still supports text chat only. Use a matching voice-enabled firmware build that uploads 16 kHz mono PCM16 WAV and plays the returned WAV through the MAX98357A.


## Phase 8 voice status

The current `.ino` firmware is still text-chat-only. Phase 8 gateway voice uses `openai/gpt-audio-mini` through OpenRouter, but voice hardware is not end-to-end until firmware is updated to capture mono 16 kHz PCM16 WAV from the INMP441, upload it to `/api/device/voice` with device credentials, fetch the returned WAV, and play the WAV format/sample rate supported by the MAX98357A path. Do not assume the existing sketch implements these steps yet.
