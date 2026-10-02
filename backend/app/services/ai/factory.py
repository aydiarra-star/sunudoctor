"""Factory that returns the configured AI providers.

Swapping a provider is a configuration change, not a code change. When a real
provider is requested but its credentials are missing, the factory falls back to
the demonstration provider AND reports that fallback (``is_demo`` + ``reason``)
so the UI can be honest about what is running. It never silently pretends a real
service is connected.
"""
from __future__ import annotations

from app.core.config import settings
from app.services.ai import safety as safety_engine
from app.services.ai.base import (
    AIValidationProvider,
    ClinicalAIProvider,
    LanguageDetectionProvider,
    ProviderSelection,
    SafetyProvider,
    SpeechToTextProvider,
    TranslationProvider,
)
from app.services.ai.demo_providers import (
    DemoAIValidation,
    DemoClinicalAI,
    DemoLanguageDetection,
    DemoSpeechToText,
    DemoTranslation,
)
from app.services.ai.real_providers import (
    AzureSpeechToTextProvider,
    OpenAIClinicalAIProvider,
)


class RuleBasedSafety(SafetyProvider):
    """Local, deterministic safety provider. No external call, always available."""

    name = "rule-based-safety"

    def review(self, note, transcription):
        return safety_engine.review(note, transcription)


def select_stt_provider() -> ProviderSelection:
    if (
        settings.stt_provider == "azure"
        and settings.azure_speech_key
        and settings.azure_speech_region
    ):
        return ProviderSelection(
            provider=AzureSpeechToTextProvider(
                settings.azure_speech_key,
                settings.azure_speech_region,
                settings.azure_speech_endpoint,
            ),
            is_demo=False,
            requested="azure",
        )
    reason = (
        "STT_PROVIDER=azure mais AZURE_SPEECH_KEY/AZURE_SPEECH_REGION absents."
        if settings.stt_provider == "azure"
        else "Aucun moteur de reconnaissance vocale réel configuré."
    )
    return ProviderSelection(
        provider=DemoSpeechToText(), is_demo=True, requested=settings.stt_provider, reason=reason
    )


def select_clinical_ai_provider() -> ProviderSelection:
    if settings.clinical_ai_configured:
        return ProviderSelection(
            provider=OpenAIClinicalAIProvider(
                settings.openai_api_key, settings.clinical_ai_model, settings.openai_base_url
            ),
            is_demo=False,
            requested="openai",
        )
    reason = (
        "CLINICAL_AI_PROVIDER=openai mais OPENAI_API_KEY absent."
        if settings.clinical_ai_provider == "openai"
        else "Aucun fournisseur d'IA clinique réel configuré."
    )
    return ProviderSelection(
        provider=DemoClinicalAI(),
        is_demo=True,
        requested=settings.clinical_ai_provider,
        reason=reason,
    )


def select_translation_provider() -> ProviderSelection:
    if settings.translation_configured:
        # A real translation provider is not bundled yet; the interface exists.
        return ProviderSelection(
            provider=DemoTranslation(),
            is_demo=True,
            requested="openai",
            reason="Fournisseur de traduction réel non implémenté (interface prête).",
        )
    return ProviderSelection(
        provider=DemoTranslation(),
        is_demo=True,
        requested=settings.translation_provider,
        reason="Aucun fournisseur de traduction réel configuré.",
    )


def select_language_detection_provider() -> ProviderSelection:
    """Heuristic detection. A real provider could be swapped in without code change."""
    return ProviderSelection(
        provider=DemoLanguageDetection(),
        is_demo=True,
        requested="heuristic",
        reason="Détection heuristique locale (aucun service de détection externe configuré).",
    )


def select_ai_validation_provider() -> ProviderSelection:
    """Deterministic draft review. Never adds or corrects clinical content."""
    return ProviderSelection(
        provider=DemoAIValidation(),
        is_demo=True,
        requested="deterministic",
        reason="Revue de brouillon déterministe locale.",
    )


def get_safety_provider() -> SafetyProvider:
    return RuleBasedSafety()


# --- Backwards-compatible accessors (provider, is_demo) ---------------------
def get_stt_provider() -> tuple[SpeechToTextProvider, bool]:
    sel = select_stt_provider()
    return sel.provider, sel.is_demo


def get_clinical_ai_provider() -> tuple[ClinicalAIProvider, bool]:
    sel = select_clinical_ai_provider()
    return sel.provider, sel.is_demo


def get_translation_provider() -> tuple[TranslationProvider, bool]:
    sel = select_translation_provider()
    return sel.provider, sel.is_demo


def get_language_detection_provider() -> tuple[LanguageDetectionProvider, bool]:
    sel = select_language_detection_provider()
    return sel.provider, sel.is_demo


def get_ai_validation_provider() -> tuple[AIValidationProvider, bool]:
    sel = select_ai_validation_provider()
    return sel.provider, sel.is_demo


def provider_status() -> dict:
    """Honest capability report for /api/meta and the /status page."""
    return {
        "stt": {
            "requested": settings.stt_provider,
            "connected": settings.stt_configured,
            "provider": "azure-stt" if settings.stt_configured else "demo-stt",
            "reason": select_stt_provider().reason,
        },
        "clinical_ai": {
            "requested": settings.clinical_ai_provider,
            "connected": settings.clinical_ai_configured,
            "provider": (
                "openai-clinical" if settings.clinical_ai_configured else "demo-clinical"
            ),
            "model": (
                settings.clinical_ai_model
                if settings.clinical_ai_configured
                else "demo-extractive-v1"
            ),
            "reason": select_clinical_ai_provider().reason,
        },
        "translation": {
            "requested": settings.translation_provider,
            "connected": settings.translation_configured,
            "provider": "demo-translation",
            "reason": select_translation_provider().reason,
        },
        "language_detection": {
            "requested": "heuristic",
            "connected": False,
            "provider": "demo-language-detection",
            "reason": select_language_detection_provider().reason,
        },
        "safety": {
            "requested": "rule-based",
            "connected": True,
            "provider": "rule-based-safety",
            "reason": "Garde-fou déterministe local, toujours actif.",
        },
    }
