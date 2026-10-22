from types import SimpleNamespace

import app.main as main


def test_nvidia_is_default_provider_and_uses_compatible_endpoint(monkeypatch):
    assert main.settings.chat_provider == "nvidia"
    assert main.settings.nvidia_base_url == "https://integrate.api.nvidia.com/v1"
    assert "nemotron" in main.settings.chat_model.lower()


def test_generate_chat_answer_routes_to_nvidia_and_selected_model(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="NVIDIA response"))])

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(main.settings, "nvidia_api_key", "test-nvidia-key")
    monkeypatch.setattr(main.settings, "chat_provider", "nvidia")
    monkeypatch.setattr(main, "model_client", lambda provider: fake_client if provider == "nvidia" else None)

    assert main.generate_chat_answer("Hello") == "NVIDIA response"
    assert captured["model"] == main.settings.chat_model
    assert captured["messages"][-1]["content"] == "Hello"


def test_unknown_provider_fails_clearly():
    try:
        main.model_client("unsupported-provider")
    except RuntimeError as exc:
        assert "Use nvidia or openrouter" in str(exc)
    else:
        raise AssertionError("Unknown provider should fail")
