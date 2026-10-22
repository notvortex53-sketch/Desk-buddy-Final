# Desk Buddy Phase 10 — NVIDIA NIM

## What changed

- NVIDIA NIM is the default provider for `/api/chat` and Ethical Mode review.
- Provider selection is configurable (`CHAT_PROVIDER`, `ETHICAL_PROVIDER`); supported compatible providers are `nvidia` and `openrouter`.
- `/health` reports provider configuration state without exposing secrets.
- Existing OpenRouter audio request/response code is retained separately. NVIDIA text chat does **not** automatically replace the audio pipeline.
- Device pairing, WebSocket protocol, Netlify bridge, and agent action allowlists are unchanged.

## Render environment

Set these in Render → Desk Buddy service → Environment:

```env
CHAT_PROVIDER=nvidia
ETHICAL_PROVIDER=nvidia
NVIDIA_API_KEY=<your NVIDIA API key>
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
CHAT_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
ETHICAL_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
```

The model ID above is a starting default from NVIDIA's published NIM catalog, not a guarantee that the model is enabled for every account. If NVIDIA reports model-not-found or access denied, choose an enabled chat model in the NVIDIA API Catalog and update both model variables as appropriate. Never commit a real API key to GitHub or place it in ESP32 firmware.

The current audio route still needs these if voice is to work through its existing provider:

```env
OPENROUTER_API_KEY=<optional for chat; needed by current voice route>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
VOICE_MODEL=openai/gpt-audio-mini
VOICE_NAME=alloy
```

If OpenRouter has no available credits, text chat can still work through NVIDIA after the NVIDIA key and model are valid, but voice requests may continue to fail until the voice integration is migrated to an audio-capable provider.

## Deploy and verify

1. Push the updated `Desk-buddy` repository to GitHub (or upload this package to the matching repository).
2. Add the NVIDIA environment variables in Render; do not paste the API key into source files.
3. Deploy the latest commit.
4. Open `/health`; expect `chat_provider` and `ethical_provider` to be `nvidia`, and `nvidia_configured` / `chat_configured` to be `true`. `voice_configured` may be `false` if OpenRouter is not configured.
5. Test `/api/chat` from the existing authenticated bridge. If it returns 502, inspect Render logs for NVIDIA's actual response and verify API key, selected model access, rate limits, and quota.
6. Test Ethical Mode with an explicitly approved, allowlisted action. If model review fails, the gateway intentionally fails closed.

## Verification status

- Automated gateway tests: 27 passed locally after this change.
- Live NVIDIA credentials/model: not tested in this environment.
- Render deployment: not triggered by this package.
- Physical ESP32 audio path: not validated; current audio pipeline is unchanged.
