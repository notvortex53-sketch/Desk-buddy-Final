# Desk Buddy Gateway

FastAPI gateway for Desk Buddy pairing, authenticated device WebSockets, chat, allowlisted tasks, Ethical Mode review, and Phase 8 voice.

## Configure

Copy `.env.example` to `.env`. Set `DEVICE_TOKEN_PEPPER`, `RESEND_API_KEY`, and `EMAIL_FROM`. Phase 10 uses NVIDIA NIM for text chat and Ethical Mode by default: set `NVIDIA_API_KEY`, `NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1`, `CHAT_PROVIDER=nvidia`, `ETHICAL_PROVIDER=nvidia`, and the model IDs in `.env.example`. NVIDIA publishes the current model catalog at https://docs.api.nvidia.com/nim/reference/llm-apis; availability can vary by account, so choose a model actually enabled in your NVIDIA API Catalog. OpenRouter is now optional and remains only for the existing voice/audio path (`VOICE_MODEL=openai/gpt-audio-mini`). If OpenRouter credits are exhausted, text chat can still work through NVIDIA but the current audio pipeline will remain unavailable until its provider is separately migrated to a compatible speech model. Use PostgreSQL for production; SQLite is for local development only.

## Phase 8 voice API

`POST /api/device/voice` accepts bounded mono 16 kHz PCM16 WAV bytes with `X-Device-ID` and `X-Device-Token`. It returns answer text and a temporary audio URL. This model integration does not separately expose a reliable transcript of the incoming recording. Download the audio from `GET /api/device/voice/{audio_id}/audio` using the same headers. This is request/response audio, not continuous streaming. See `docs/protocol.md`.

## Ethical Mode

Windows tasks require owner approval and an additional NVIDIA NIM model review of the allowlisted action by default; `ETHICAL_PROVIDER=openrouter` can select OpenRouter instead. Review failures and denials fail closed. The model does not replace code-level permission checks or the agent action allowlist.

## Test

From this directory, install `requirements.txt`, then run `pytest -q`. Tests mock provider calls; a live NVIDIA API request and physical ESP32 audio test are separate verification steps.
