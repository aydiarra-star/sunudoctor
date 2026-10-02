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
    openai_base_url: str = "https://api.openai.com/v1"
    clinical_ai_model: str = "gpt-4o-mini"
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    azure_speech_endpoint: str = ""
    # Transcription: default recognition language when the caller has no hint.
    stt_default_language: str = "wo-SN"
    # Maximum accepted audio upload (bytes). Guards against abuse.
    max_audio_bytes: int = 25 * 1024 * 1024

    # Teleconsultation / WebRTC. Signalling is a short-lived, authenticated,
    # single-room token flow. ICE servers (STUN/TURN) must be provided by the
    # operator; without them video stays "configuration requise".
    turn_url: str = ""
    turn_username: str = ""
    turn_password: str = ""
    stun_urls: str = "stun:stun.l.google.com:19302"
    teleconsultation_token_ttl_minutes: int = 30

    # Payments. Keys stay server-side only. Webhooks are verified server-side.
    payment_mode: Literal["demo", "live"] = "demo"
    wave_api_key: str = ""
    wave_webhook_secret: str = ""
    orange_money_api_key: str = ""
    orange_money_webhook_secret: str = ""
    card_provider_api_key: str = ""
    card_webhook_secret: str = ""

    # Trial period for new subscriptions (days).
    trial_days: int = 14

    # Rate limiting (per client IP, per window) for auth/billing endpoints.
    rate_limit_requests: int = 60
    rate_limit_window: int = 60

    # Optional: path to a built frontend to serve as a single-origin SPA.
    frontend_dist: str = ""

    # Health facility registry. SunuDoctor never fabricates a referential and
    # never scrapes a protected system. An official or partner integration is
    # only used when an authorised endpoint and credential are supplied.
    official_registry_url: str = ""
    official_registry_key: str = ""
    partner_registry_url: str = ""
    partner_registry_key: str = ""
    # Minimum similarity score for a facility candidate to be surfaced. A match
    # is only ever informational: it never validates a professional on its own.
    facility_match_threshold: float = 0.55
    # Minimum professional-verification level required to author clinical data.
    require_verified_professional: bool = True

    # Roles for which MFA is mandatory. Enforced at login when the user has MFA
    # enabled; operators should require enrolment for these roles.
    mfa_required_for_roles: str = "admin,structure_admin"

    @property
    def mfa_required_role_list(self) -> list[str]:
        return [r.strip() for r in self.mfa_required_for_roles.split(",") if r.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def production_problems(self) -> list[str]:
        """Return a list of reasons the current config is unsafe for production.

        Empty means safe. This is deliberately conservative: it names every
        problem at once so an operator can fix them together. It never silently
        upgrades a demo capability to "live".
        """
        problems: list[str] = []
        if self.secret_key == "dev-only-insecure-change-me" or len(self.secret_key) < 32:
            problems.append("SECRET_KEY doit être défini et faire au moins 32 caractères.")
        if self.database_url.startswith("sqlite"):
            problems.append("DATABASE_URL doit pointer vers PostgreSQL en production.")
        if self.ai_mode == "live":
            if self.stt_provider != "demo" and not self.stt_configured:
                problems.append(
                    f"STT_PROVIDER={self.stt_provider} sélectionné mais aucune clé fournie."
                )
            if self.clinical_ai_provider != "demo" and not self.clinical_ai_configured:
                problems.append(
                    f"CLINICAL_AI_PROVIDER={self.clinical_ai_provider} sélectionné mais "
                    "OPENAI_API_KEY est absent."
                )
        if self.payment_mode == "live":
            if not any(self.payment_provider_configured.values()):
                problems.append("PAYMENT_MODE=live mais aucun fournisseur n'est configuré.")
            if not any(self.webhook_secrets.values()):
                problems.append(
                    "PAYMENT_MODE=live mais aucun secret de webhook n'est configuré "
                    "(les paiements ne pourraient pas être confirmés de façon fiable)."
                )
        return problems

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_demo(self) -> bool:
        return self.ai_mode == "demo"

    # --- Capability helpers: these decide whether a feature is really connected.
    # They are the single source of truth used by the API, the factory and the
    # honesty endpoints. A feature is "live" only when BOTH the provider is
    # selected AND its credential is present.
    @property
    def stt_configured(self) -> bool:
        if self.stt_provider == "azure":
            return bool(self.azure_speech_key and self.azure_speech_region)
        if self.stt_provider == "openai":
            return bool(self.openai_api_key)
        return False

    @property
    def clinical_ai_configured(self) -> bool:
        return self.clinical_ai_provider == "openai" and bool(self.openai_api_key)

    @property
    def translation_configured(self) -> bool:
        return self.translation_provider == "openai" and bool(self.openai_api_key)

    @property
    def turn_configured(self) -> bool:
        return bool(self.turn_url)

    @property
    def ice_servers(self) -> list[dict]:
        servers: list[dict] = []
        stuns = [s.strip() for s in self.stun_urls.split(",") if s.strip()]
        if stuns:
            servers.append({"urls": stuns})
        if self.turn_url:
            entry: dict = {"urls": [self.turn_url]}
            if self.turn_username:
                entry["username"] = self.turn_username
            if self.turn_password:
                entry["credential"] = self.turn_password
            servers.append(entry)
        return servers

    @property
    def payment_provider_configured(self) -> dict[str, bool]:
        return {
            "wave": bool(self.wave_api_key),
            "orange_money": bool(self.orange_money_api_key),
            "card": bool(self.card_provider_api_key),
            "bank": False,
            "other": False,
        }

    @property
    def webhook_secrets(self) -> dict[str, str]:
        return {
            "wave": self.wave_webhook_secret,
            "orange_money": self.orange_money_webhook_secret,
            "card": self.card_webhook_secret,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
