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

    # One OpenRouter credential serves every model. No provider-specific AI keys.
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    chat_model: str = "anthropic/claude-sonnet-4.6"
    ethical_model: str = "anthropic/claude-sonnet-4.6"
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
    def openrouter_configured(self) -> bool:
        return bool(self.openrouter_api_key.strip() and self.openrouter_base_url.strip())


settings = Settings()
