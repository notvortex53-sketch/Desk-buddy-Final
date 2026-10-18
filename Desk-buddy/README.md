Desk Buddy Gateway
FastAPI service for OTP pairing, owner sessions, device registry/revocation, authenticated WebSockets, allow-listed task dispatch/results, and OpenRouter-powered Claude chat/Ethical Mode and GPT Audio Mini voice.
Local development (Windows PowerShell)
```powershell
cd gateway
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
py -c "import secrets; print(secrets.token_urlsafe(48))"
# Paste the generated value into DEVICE_TOKEN_PEPPER in .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Configure Resend before pairing by setting `RESEND_API_KEY` and `EMAIL_FROM`. `onboarding@resend.dev` is for limited Resend testing; for production, verify your domain in Resend and set `EMAIL_FROM` to an authorized sender on that domain. Keep the API key only in the server environment (for example, Render), never in frontend code or GitHub. Configure `CORS_ORIGINS` to exact browser origins. Set `OPENROUTER_API_KEY` once to enable chat, voice, and Ethical Mode. The default models are `anthropic/claude-sonnet-4.6` for chat/ethical review and `openai/gpt-audio-mini` for voice. Use PostgreSQL in production; the default SQLite database is for local development only.
API summary
`GET /health` — service/configuration status; does not reveal secrets.
`POST /api/pair/start` and `POST /api/pair/verify` — email OTP pairing.
`GET /api/auth/me`, `POST /api/auth/logout` — owner session.
`GET /api/devices`, `DELETE /api/devices/{device_id}` — owner-scoped device management.
`POST /api/tasks`, `GET /api/tasks/{task_id}` — safe task dispatch and result polling.
`POST /api/chat` — optional model chat.
`WS /ws/device` — authenticated device connection.
See `gateway/docs/protocol.md` for message contracts and connector support. WebSocket presence is process-local; use a shared broker before running multiple workers.

## Phase 7 — ESP32-C3 Mini firmware

The ESP32-C3 firmware is in [`esp32_c3/`](esp32_c3/). See [`esp32_c3/README.md`](esp32_c3/README.md) for setup, required Arduino libraries, TLS requirements, pairing credentials, and current backend limits. Copy `esp32_c3/config.example.h` to `esp32_c3/config.h` and keep the real config private.


## Phase 8 — OpenRouter voice + Claude Ethical Mode

The gateway accepts authenticated mono 16 kHz PCM16 WAV recordings at `POST /api/device/voice`, sends audio to `openai/gpt-audio-mini` through OpenRouter, and returns answer text and a temporary authenticated WAV download URL (the model does not separately return a reliable input transcript in this integration) for playback. This is request/response audio, not an always-open full-duplex Realtime session.

Configure in Render: `OPENROUTER_API_KEY` (the only AI-provider key), `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`, `VOICE_MODEL=openai/gpt-audio-mini`, `CHAT_MODEL=anthropic/claude-sonnet-4.6`, `ETHICAL_MODEL=anthropic/claude-sonnet-4.6`, and `VOICE_NAME=alloy`. Resend remains a separate email OTP service, not an AI provider.

Windows tasks require explicit owner approval and a Claude Sonnet 4.6 Ethical Mode review before delivery. Review errors or denials stop the task. The gateway and agent allowlists remain the actual enforcement boundary.

**Hardware status:** the included ESP32-C3 sketch is still text-chat-only. The gateway voice API and tests do not mean the INMP441 capture, WAV upload, WAV download, and MAX98357A playback flow has been tested on the physical board.
