"""Provider interfaces for the clinical AI pipeline.

The application is never coupled to a single vendor. Four interfaces are
defined and can be swapped independently:

- SpeechToTextProvider : audio -> text
- ClinicalAIProvider   : text -> structured note (extraction only, no invention)
- TranslationProvider  : translation between Wolof / French (and future languages)
- SafetyProvider       : post-processing guard against hallucination

Every result carries an ``is_demo`` flag. When a provider is not really
connected, ``is_demo`` is True and the caller must label the output as
"Mode démonstration".
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TranscriptionResult:
    raw_text: str
    language: str = "wolof"
    provider: str = "demo"
    is_demo: bool = True
    uncertain_spans: list[str] = field(default_factory=list)


@dataclass
class StructuredField:
    """A single structured field. ``uncertain`` means a human must verify."""

    value: str | None = None
    uncertain: bool = False
    source_span: str | None = None


@dataclass
class StructuredNote:
    chief_complaint: StructuredField = field(default_factory=StructuredField)
    history: StructuredField = field(default_factory=StructuredField)
    symptoms: list[StructuredField] = field(default_factory=list)
    negated_symptoms: list[str] = field(default_factory=list)
    history_items: list[StructuredField] = field(default_factory=list)
    allergies: list[StructuredField] = field(default_factory=list)
    medications: list[dict] = field(default_factory=list)
    vitals: list[dict] = field(default_factory=list)
    exam: StructuredField = field(default_factory=StructuredField)
    investigations: StructuredField = field(default_factory=StructuredField)
    diagnosis: StructuredField = field(default_factory=StructuredField)
    decision: StructuredField = field(default_factory=StructuredField)
    prescription: StructuredField = field(default_factory=StructuredField)
    recommendations: StructuredField = field(default_factory=StructuredField)
    follow_up: StructuredField = field(default_factory=StructuredField)
    uncertainties: list[str] = field(default_factory=list)
    provider: str = "demo"
    is_demo: bool = True
    model: str = "demo-extractive-v1"

    def to_dict(self) -> dict:
        def f(x: StructuredField) -> dict:
            return {"value": x.value, "uncertain": x.uncertain, "source_span": x.source_span}

        return {
            "chief_complaint": f(self.chief_complaint),
            "history": f(self.history),
            "symptoms": [f(s) for s in self.symptoms],
            "negated_symptoms": self.negated_symptoms,
            "history_items": [f(s) for s in self.history_items],
            "allergies": [f(s) for s in self.allergies],
            "medications": self.medications,
            "vitals": self.vitals,
            "exam": f(self.exam),
            "investigations": f(self.investigations),
            "diagnosis": f(self.diagnosis),
            "decision": f(self.decision),
            "prescription": f(self.prescription),
            "recommendations": f(self.recommendations),
            "follow_up": f(self.follow_up),
            "uncertainties": self.uncertainties,
            "provider": self.provider,
            "is_demo": self.is_demo,
            "model": self.model,
        }


class SpeechToTextProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def transcribe(
        self, audio: bytes | None, *, language_hint: str = "wolof", text_hint: str | None = None
    ) -> TranscriptionResult:
        """Convert audio to text. Must never invent content not present in input."""


class ClinicalAIProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def structure(self, transcription: str, *, language: str = "wolof") -> StructuredNote:
        """Extract a structured note. Extraction only: never invent clinical facts."""


class TranslationProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def translate(self, text: str, *, source: str, target: str) -> tuple[str, bool]:
        """Return (translated_text, is_demo)."""


class SafetyProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def review(self, note: StructuredNote, transcription: str) -> tuple[StructuredNote, list[str]]:
        """Return (sanitised_note, flags). Must never add clinical content."""
