# Desk Buddy Phase 8 Retry — OpenRouter Voice + Claude Ethical Mode

## Implemented

- Unified AI configuration through `https://openrouter.ai/api/v1` with one `OPENROUTER_API_KEY`.
- `openai/gpt-audio-mini` for authenticated request/response audio input and spoken audio output.
- `anthropic/claude-sonnet-4.6` for chat and an additional Ethical Mode review before Windows allowlisted tasks are dispatched.
- Fail-closed behavior: if the ethical review fails, is malformed, or denies a task, the gateway does not send it to the Windows agent. Existing explicit owner approval and code-level action allowlists remain required.
- Health endpoint reports model IDs/configuration presence without revealing credentials.
- Updated Render environment configuration, `.env.example`, protocol documentation, README files, and tests.
- Removed local SQLite databases from the delivery package; `.gitignore` ignores local databases and `.env` files.

## Local verification

- `python -m compileall -q app` — passed.
- `pytest -q` — 24 passed. Provider calls in tests are mocked; no live OpenRouter request was made.

## Not yet verified

- Live OpenRouter access for both selected model IDs, account billing/limits, and exact provider audio response behavior.
- Render deployment and real ESP32-C3 audio capture/upload/download/playback. The included ESP32 firmware remains text-chat-only; Phase 8 audio requires a matching firmware update before hardware voice works end to end.
- The voice API is request/response, not persistent full-duplex Realtime streaming. Audio replies are temporary and process-local; keep one gateway worker/instance for this version.

## Render variables

Required AI setting: `OPENROUTER_API_KEY` (secret).

Defaults: `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`, `CHAT_MODEL=anthropic/claude-sonnet-4.6`, `ETHICAL_MODEL=anthropic/claude-sonnet-4.6`, `VOICE_MODEL=openai/gpt-audio-mini`, `VOICE_NAME=alloy`, `MODEL_TIMEOUT_SECONDS=60`.

`RESEND_API_KEY` is still required for email OTP and is not an AI model key. Keep all secrets in Render environment settings, never in firmware, frontend code, or GitHub.
