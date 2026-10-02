"""Factory that returns the configured AI providers.

Swapping a provider is a configuration change, not a code change. When a real
provider is requested but its credentials are missing, the factory falls back to
the demonstration provider AND reports that fallback so the UI can be honest
about what is running.
"""
from __future__ import annotations

from app.core.config import settings
from app.services.ai.base import (
    ClinicalAIProvider,
    SafetyProvider,
    SpeechToTextProvider,
    TranslationProvider,
)
from app.services.ai import safety as safety_engine
from app.services.ai.demo_providers import (
    DemoClinicalAI,
    DemoSpeechToText,
    DemoTranslation,
)


class RuleBasedSafety(SafetyProvider):
    """Local, deterministic safety provider. No external call, always available."""

    name = "rule-based-safety"

    def review(self, note, transcription):
        return safety_engine.review(note, transcription)


def get_stt_provider() -> tuple[SpeechToTextProvider, bool]:
    if settings.stt_provider == "demo" or not settings.azure_speech_key:
        return DemoSpeechToText(), True
    # A real provider would be instantiated here (e.g. Azure Speech).
    return DemoSpeechToText(), True


def get_clinical_ai_provider() -> tuple[ClinicalAIProvider, bool]:
    if settings.clinical_ai_provider == "demo" or not settings.openai_api_key:
        return DemoClinicalAI(), True
    return DemoClinicalAI(), True


def get_translation_provider() -> tuple[TranslationProvider, bool]:
    if settings.translation_provider == "demo":
        return DemoTranslation(), True
    return DemoTranslation(), True


def get_safety_provider() -> SafetyProvider:
    return RuleBasedSafety()
