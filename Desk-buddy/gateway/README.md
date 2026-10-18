# Desk Buddy Gateway

FastAPI gateway for Desk Buddy pairing, authenticated device WebSockets, chat, allowlisted tasks, Ethical Mode review, and Phase 8 voice.

## Configure

Copy `.env.example` to `.env`. Set `DEVICE_TOKEN_PEPPER`, `RESEND_API_KEY`, `EMAIL_FROM`, and one `OPENROUTER_API_KEY`. AI requests use `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`; default `CHAT_MODEL` and `ETHICAL_MODEL` are `anthropic/claude-sonnet-4.6`, and `VOICE_MODEL` is `openai/gpt-audio-mini`. No separate OpenAI, Anthropic, or Groq API key is used. Use PostgreSQL for production; SQLite is for local development only.

## Phase 8 voice API

`POST /api/device/voice` accepts bounded mono 16 kHz PCM16 WAV bytes with `X-Device-ID` and `X-Device-Token`. It returns answer text and a temporary audio URL. This model integration does not separately expose a reliable transcript of the incoming recording. Download the audio from `GET /api/device/voice/{audio_id}/audio` using the same headers. This is request/response audio, not continuous streaming. See `docs/protocol.md`.

## Ethical Mode

Windows tasks require owner approval and an additional Claude Sonnet review of the allowlisted action. Review failures and denials fail closed. The model does not replace code-level permission checks or the agent action allowlist.

## Test

From this directory, install `requirements.txt`, then run `pytest -q`. Tests mock provider calls; a live OpenRouter API request and physical ESP32 audio test are separate verification steps.
