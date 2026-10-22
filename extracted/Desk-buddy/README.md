Desk Buddy Gateway
FastAPI service for OTP pairing, owner sessions, device registry/revocation, authenticated WebSockets, allow-listed task dispatch/results, NVIDIA NIM-powered chat/Ethical Mode, and the existing optional OpenRouter GPT Audio Mini voice pipeline.
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
Configure Resend before pairing by setting `RESEND_API_KEY` and `EMAIL_FROM`. `onboarding@resend.dev` is for limited Resend testing; for production, verify your domain in Resend and set `EMAIL_FROM` to an authorized sender on that domain. Keep the API key only in the server environment (for example, Render), never in frontend code or GitHub. Configure `CORS_ORIGINS` to exact browser origins. Phase 10 uses NVIDIA NIM for text chat and Ethical Mode: set `NVIDIA_API_KEY`, `NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1`, `CHAT_PROVIDER=nvidia`, and `ETHICAL_PROVIDER=nvidia`. The default text model is `nvidia/nemotron-3.5-lightning-30b-a3b`; select an available model from NVIDIA’s API Catalog if this model is not enabled for your account. `OPENROUTER_API_KEY` is optional and currently only powers the existing audio pipeline (`VOICE_MODEL=openai/gpt-audio-mini`); if OpenRouter has no usable credits, voice requests may still fail even when NVIDIA chat works. Use PostgreSQL in production; the default SQLite database is for local development only.
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


## Phase 8 — OpenRouter voice pipeline

The gateway accepts authenticated mono 16 kHz PCM16 WAV recordings at `POST /api/device/voice`, sends audio to `openai/gpt-audio-mini` through OpenRouter, and returns answer text and a temporary authenticated WAV download URL (the model does not separately return a reliable input transcript in this integration) for playback. This is request/response audio, not an always-open full-duplex Realtime session.

Configure in Render: `OPENROUTER_API_KEY` (optional, for voice only), `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`, `VOICE_MODEL=openai/gpt-audio-mini`, and `VOICE_NAME=alloy`. Text chat and Ethical Mode use NVIDIA NIM in Phase 10. Resend remains a separate email OTP service, not an AI provider.

Windows tasks require explicit owner approval and an NVIDIA NIM Ethical Mode review before delivery. Review errors or denials stop the task. The gateway and agent allowlists remain the actual enforcement boundary.

**Hardware status:** the included ESP32-C3 sketch is still text-chat-only. The gateway voice API and tests do not mean the INMP441 capture, WAV upload, WAV download, and MAX98357A playback flow has been tested on the physical board.


## Phase 10 — NVIDIA NIM

The gateway now routes chat and Ethical Mode through NVIDIA NIM by default, using the OpenAI-compatible `POST /v1/chat/completions` API. Set `NVIDIA_API_KEY` in Render as a secret. Check `/health` for `chat_provider`, `chat_configured`, `ethical_configured`, `nvidia_configured`, and `voice_configured`. The health endpoint never returns keys. The live NVIDIA API and selected model still need an authenticated smoke test after deployment. Voice remains a separate OpenRouter audio integration and is not migrated by this phase.
