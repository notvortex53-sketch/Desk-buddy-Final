# Device WebSocket protocol

Connect an ESP32-C3 directly to `wss://<Render-service-host>/ws/device`.  Do
not put the credential in the URL, a query string, or an HTTP header.  After
the WebSocket upgrade, send this JSON object within 10 seconds:

```json
{"type":"auth","device_id":"<paired-device-id>","token":"<device-token>"}
```

On success the gateway replies:

```json
{"type":"authenticated","device_id":"<paired-device-id>","heartbeat_seconds":25}
```

Send `{"type":"ping"}` at least once per advertised interval.  The gateway
replies with `{"type":"pong","time":"<ISO-8601 UTC timestamp>"}`.  Any
valid device message refreshes `last_seen_at`; silence for two heartbeat
intervals closes the connection with code `4408`.  Devices should reconnect
with exponential backoff and repeat `auth` after every new connection.

Windows and Android agents also receive `reauthenticate_after_seconds` in the
successful authentication message. The gateway closes their socket with code
`4003` when that period elapses; the agent must reconnect and authenticate
again using its paired credential.

Other device-to-gateway messages are `status`, which receives `status_ack`,
`chat`, and `task_result`. A chat request uses a device-generated request ID
to correlate a later response:

```json
{"type":"chat","request_id":"<unique request ID>","message":"Hello, Buddy"}
```

On success the gateway replies with `chat_response` carrying the same
`request_id`, the `answer`, and the configured `model`. It returns
`chat_error` with `invalid_request`, `model_unavailable`, or
`model_request_failed` when the request cannot be completed. Retain the
request ID until either response arrives; after a disconnect, reconnect and
submit a new chat request with a new request ID.

A task result uses:

```json
{"type":"task_result","task_id":"<task UUID>","ok":true,"result":"optional text"}
```

The gateway acknowledges accepted results with `task_result_ack`.  Gateway
task delivery is `{"type":"task","task_id":"<task UUID>","action":{...}}`.
Only the existing `get_status` and `open_url` actions are accepted by the REST
task API.

## Ethical Mode for Windows

Routing a task to a Windows device requires the authenticated owner to submit
`"ethical_mode_approved": true` in the task request. The gateway rejects an
unapproved Windows task with HTTP 403 and adds a gateway-side authorization
object to approved task messages. The Windows agent independently
rejects task messages without that object. Android and ESP32-C3 routing are not
changed by this Windows-specific gate.

Invalid or revoked credentials close with `4401`; a superseded connection for
the same device closes with `4000`; owner revocation closes with `4001` when
the connection is handled by the same gateway process.  The current Render
deployment must run one worker because socket presence is process-local.

## Render deployment

The existing `render.yaml` starts Uvicorn on Render's supplied `PORT`, which
supports the HTTP upgrade used by this endpoint. Set `DATABASE_URL` to a
persistent Postgres database and set a newly generated `DEVICE_TOKEN_PEPPER`
in Render's secret environment settings; do not use SQLite in production
because the Render filesystem is ephemeral. Connect ESP32-C3 firmware only to
the public `wss://` URL (not `ws://`, and with no explicit port). Keep one
Uvicorn worker/one Render instance until socket presence and task routing move
to a shared broker. Render may restart an instance or spin down an idle free
service, so firmware must reconnect with backoff after every disconnect.


## Phase 8 — OpenRouter voice and Ethical Mode

The authenticated HTTPS upload/download flow is request/response, not a persistent full-duplex stream. The ESP32 uploads a short mono 16 kHz PCM16 WAV recording to `POST /api/device/voice`; the gateway sends it to `openai/gpt-audio-mini` through OpenRouter with text+audio output requested. The response contains answer text and a temporary authenticated WAV download URL. The current audio-model response does not separately expose a reliable transcript of the incoming recording; the `transcript` field is explicitly marked as unavailable rather than mislabeling the generated answer as input transcription. Fetch the audio from `GET /api/device/voice/{audio_id}/audio` using the same device headers. Audio replies are process-local and expire after five minutes, so use a single gateway instance unless shared storage is added.

The same `OPENROUTER_API_KEY` is used for `CHAT_MODEL` and `ETHICAL_MODEL` (default `anthropic/claude-sonnet-4.6`) as well as `VOICE_MODEL` (default `openai/gpt-audio-mini`). Set `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`. Do not configure separate Anthropic, OpenAI, or Groq API keys for these model calls. `RESEND_API_KEY` remains separate because it is used only for email OTP.

For Windows tasks, the gateway requires explicit owner approval and performs an additional Ethical Mode review before sending the allowlisted action. If OpenRouter fails, returns invalid review data, or denies the action, the gateway fails closed and does not send the task. Model review is not a substitute for local allowlists and authorization checks in the gateway and agent.

Audio input constraints: uncompressed mono PCM16 WAV, 16 kHz, 0.25–12 seconds, maximum 450 KB. Audio output is validated as WAV and limited to 4 MB. The ESP32 firmware in this package is still text-chat-only; Phase 8 audio is not end-to-end on hardware until firmware capture/upload/download/playback is implemented and tested.
