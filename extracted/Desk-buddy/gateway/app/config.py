from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Desk Buddy Gateway"
    environment: str = "development"
    database_url: str = "sqlite:///./desk_buddy.db"
    cors_origins: str = "http://localhost:8888,http://127.0.0.1:8888"
    public_gateway_url: str = "http://127.0.0.1:8000"
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    pairing_rate_limit_per_hour: int = 5
    session_ttl_days: int = 30
    task_timeout_seconds: int = 120
    device_auth_timeout_seconds: int = 10
    device_heartbeat_seconds: int = 25
    windows_reauthentication_seconds: int = 3600
    android_reauthentication_seconds: int = 3600
    ethical_mode_required: bool = True
    device_token_pepper: str = ""
    resend_api_key: str = ""
    email_from: str = "onboarding@resend.dev"

    # Phase 10: NVIDIA NIM is the default provider for text chat and ethical review.
    # OpenRouter remains independently configurable for the existing audio pipeline.
    chat_provider: str = "nvidia"
    ethical_provider: str = "nvidia"
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    chat_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    ethical_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    voice_model: str = "openai/gpt-audio-mini"
    voice_name: str = "alloy"
    model_timeout_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def resend_configured(self) -> bool:
        return bool(self.resend_api_key.strip() and self.email_from.strip())

    @property
    def nvidia_configured(self) -> bool:
        return bool(self.nvidia_api_key.strip() and self.nvidia_base_url.strip())

    @property
    def openrouter_configured(self) -> bool:
        return bool(self.openrouter_api_key.strip() and self.openrouter_base_url.strip())

    @property
    def chat_configured(self) -> bool:
        provider = self.chat_provider.strip().lower()
        if provider == "nvidia":
            return self.nvidia_configured
        if provider == "openrouter":
            return self.openrouter_configured
        return False

    @property
    def ethical_configured(self) -> bool:
        provider = self.ethical_provider.strip().lower()
        if provider == "nvidia":
            return self.nvidia_configured
        if provider == "openrouter":
            return self.openrouter_configured
        return False


settings = Settings()
