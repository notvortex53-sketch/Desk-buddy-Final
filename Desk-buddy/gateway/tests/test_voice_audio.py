import io
import wave
import pytest
from app.main import validate_input_wav


def make_wav(seconds=1.0, rate=16000, channels=1, sample_width=2):
    frames = int(seconds * rate)
    data = b"\x00" * frames * channels * sample_width
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sample_width)
        w.setframerate(rate)
        w.writeframes(data)
    return out.getvalue()


def test_accepts_expected_pcm_wav():
    assert validate_input_wav(make_wav(seconds=2.0)) == 2.0


def test_rejects_stereo():
    with pytest.raises(ValueError, match="16 kHz, mono"):
        validate_input_wav(make_wav(channels=2))


def test_rejects_wrong_sample_rate():
    with pytest.raises(ValueError, match="16 kHz, mono"):
        validate_input_wav(make_wav(rate=22050))


def test_rejects_too_long_recording():
    with pytest.raises(ValueError, match="between 0.25 and 12 seconds"):
        validate_input_wav(make_wav(seconds=13))


def test_rejects_non_wav_bytes():
    with pytest.raises(ValueError, match="valid WAV"):
        validate_input_wav(b"not a wav")


def test_resample_pcm16_mono_changes_sample_count():
    from app.main import _resample_pcm16_mono
    # 160 samples at 16 kHz become approximately 240 samples at 24 kHz.
    source = b"\x00\x00" * 160
    output = _resample_pcm16_mono(source, 16000, 24000)
    assert len(output) == 240 * 2


def test_wraps_pcm_as_valid_wav():
    from app.main import _wav_bytes
    output = _wav_bytes(b"\x00\x00" * 240, 24000)
    with wave.open(io.BytesIO(output), "rb") as wav:
        assert wav.getframerate() == 24000
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getnframes() == 240


def test_openrouter_voice_uses_configured_audio_model_and_validates_output(monkeypatch):
    import asyncio
    import base64
    from types import SimpleNamespace
    import app.main as main

    output_wav = make_wav(seconds=0.5, rate=24000)
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content="Hello from Desk Buddy.",
                audio=SimpleNamespace(data=base64.b64encode(output_wav).decode("ascii"), transcript="Hello from Desk Buddy."),
            ))])

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(main.settings, "openrouter_api_key", "test-openrouter-key")
    monkeypatch.setattr(main, "openrouter_client", lambda: fake_client)
    transcript, answer, audio = asyncio.run(main.process_openrouter_voice(make_wav(seconds=0.5)))

    assert captured["model"] == main.settings.voice_model
    assert captured["modalities"] == ["text", "audio"]
    assert captured["audio"]["format"] == "wav"
    assert captured["messages"][1]["content"][1]["type"] == "input_audio"
    assert transcript.startswith("(Input transcript not returned")
    assert answer == "Hello from Desk Buddy."
    assert audio == output_wav


def test_ethical_review_parses_allowlisted_decision(monkeypatch):
    from types import SimpleNamespace
    import app.main as main

    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["model"] == main.settings.ethical_model
            assert kwargs["response_format"] == {"type": "json_object"}
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content='{"allow":true,"risk":"low","reason":"Opening a normal HTTPS page is allowed.","requires_confirmation":false}'
            ))])

    monkeypatch.setattr(main, "openrouter_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions())))
    decision = main.review_ethical_task({"name": "open_url", "args": {"url": "https://example.com"}})
    assert decision["allow"] is True
    assert decision["risk"] == "low"
