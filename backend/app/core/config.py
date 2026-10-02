"""Application configuration.

All secrets are read from environment variables. No secret is ever committed.
See `.env.example` for the full list of supported variables.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SunuDoctor API"
    environment: Literal["development", "staging", "production"] = "development"

    # Security. `secret_key` MUST be overridden in production.
    secret_key: str = "dev-only-insecure-change-me"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # CORS: comma-separated list of allowed origins.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Database. Defaults to a local SQLite file for development/tests.
    database_url: str = "sqlite:///./sunudoctor.db"

    # AI providers. When no real provider is configured the platform runs in
    # DEMONSTRATION mode with clearly labelled synthetic output.
    ai_mode: Literal["demo", "live"] = "demo"
    stt_provider: str = "demo"
    clinical_ai_provider: str = "demo"
    translation_provider: str = "demo"
    openai_api_key: str = ""
    azure_speech_key: str = ""
    azure_speech_region: str = ""

    # Payments. Keys stay server-side only.
    payment_mode: Literal["demo", "live"] = "demo"
    wave_api_key: str = ""
    orange_money_api_key: str = ""
    card_provider_api_key: str = ""

    # Trial period for new subscriptions (days).
    trial_days: int = 14

    # Rate limiting (per client IP, per window) for auth/billing endpoints.
    rate_limit_requests: int = 60
    rate_limit_window: int = 60

    # Optional: path to a built frontend to serve as a single-origin SPA.
    frontend_dist: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_demo(self) -> bool:
        return self.ai_mode == "demo"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
