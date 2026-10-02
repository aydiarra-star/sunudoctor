"""DEMONSTRATION providers.

These providers do NOT call any real AI service. They are deterministic and
strictly extractive: every value they output is a verbatim substring (or a
normalised form) of the input transcription. They therefore cannot invent
clinical content — but they are also limited, and every result is flagged
``is_demo=True`` so the UI can display "Mode démonstration".

They exist so the whole pipeline (record -> transcribe -> structure -> verify
-> validate) can be exercised end to end without any external credentials.
Replacing them with real providers requires no change to the rest of the app.
"""
from __future__ import annotations

import re

from app.services.ai.base import (
    SpeechToTextProvider,
    StructuredField,
    StructuredNote,
    TranscriptionResult,
    TranslationProvider,
    ClinicalAIProvider,
)
from app.services.ai import safety

# Symptom lexicon (French + Wolof). Used only to locate spans in the source.
SYMPTOM_TERMS = [
    "douleur", "mal", "fièvre", "fievre", "toux", "ventre", "tête", "tete",
    "gorge", "vomissement", "vomissements", "diarrhée", "diarrhee", "fatigue",
    "essoufflement", "vertige", "démangeaison", "brûlure", "brulure",
    "nausée", "nausee", "frisson", "frissons", "saignement", "constipation",
    "metti", "metit", "yaram", "biir", "bopp",  # wolof: body, belly, head
]

HISTORY_MARKERS = ["depuis", "il y a", "voici", "days", "jours", "semaine", "mois", "heure"]

# Common medication name fragments (grounded only; no dosing is inferred).
MED_TERMS = [
    "paracétamol", "paracetamol", "amoxicilline", "ibuprofène", "ibuprofene",
    "aspirine", "metformine", "amlodipine", "ors", "sérum", "serum",
    "chloroquine", "artéméther", "artemether", "coton", "fer", "acide folique",
]

VITAL_TERMS = ["température", "temperature", "tension", "pouls", "poids", "taille", "spo2"]


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[.;\n]|,\s*(?=(?:et|puis|mais|te)\b)", text)
    return [p.strip() for p in parts if p.strip()]


class DemoSpeechToText(SpeechToTextProvider):
    name = "demo-stt"

    def transcribe(
        self, audio: bytes | None, *, language_hint: str = "wolof", text_hint: str | None = None
    ) -> TranscriptionResult:
        # Without a real STT engine we cannot decode audio. We never fabricate a
        # transcript from audio bytes. In demo mode the caller may supply a text
        # hint (typed by the user) which is treated as the raw transcript.
        if text_hint:
            return TranscriptionResult(
                raw_text=text_hint.strip(),
                language=language_hint,
                provider=self.name,
                is_demo=True,
                uncertain_spans=[],
            )
        return TranscriptionResult(
            raw_text="",
            language=language_hint,
            provider=self.name,
            is_demo=True,
            uncertain_spans=["Aucun moteur de reconnaissance vocale réel n'est configuré."],
        )


class DemoClinicalAI(ClinicalAIProvider):
    name = "demo-clinical"

    def structure(self, transcription: str, *, language: str = "wolof") -> StructuredNote:
        note = StructuredNote(provider=self.name, is_demo=True)
        sentences = _sentences(transcription)

        symptom_spans: list[tuple[str, str]] = []
        history_spans: list[str] = []
        for s in sentences:
            low = safety.normalize(s)
            if any(t in low for t in (safety.normalize(t) for t in SYMPTOM_TERMS)):
                symptom_spans.append((s, s))
            if any(m in low for m in (safety.normalize(m) for m in HISTORY_MARKERS)):
                history_spans.append(s)

        # Chief complaint: first clause mentioning a symptom, verbatim.
        if symptom_spans:
            note.chief_complaint = StructuredField(value=symptom_spans[0][0])

        # History: the temporal clause if any.
        if history_spans:
            note.history = StructuredField(value=" ".join(history_spans))

        # Symptoms, preserving negation.
        for clause, _ in symptom_spans:
            if safety.contains_negation(clause):
                neg = clause
                note.negated_symptoms.append(neg)
            else:
                note.symptoms.append(StructuredField(value=clause, source_span=clause))

        # Medications: only names literally present. No dose inference.
        low_all = safety.normalize(transcription)
        for term in MED_TERMS:
            if safety.normalize(term) in low_all:
                note.medications.append(
                    {"name": term, "dose": None, "uncertain": False, "source": "transcription"}
                )

        # Vitals: keep only if the number appears in the source.
        for term in VITAL_TERMS:
            m = re.search(re.escape(term) + r"[^0-9]{0,12}(\d+[.,]?\d*)", transcription, re.I)
            if m:
                note.vitals.append(
                    {"label": term, "value": m.group(1).replace(",", "."), "unit": None}
                )

        # Explicit uncertainty markers become uncertain spans.
        for s in sentences:
            if safety.contains_uncertainty(s):
                note.uncertainties.append(s)

        # Sanitise (grounding, negation, no auto-diagnosis).
        note, _flags = safety.review(note, transcription)
        return note


class DemoTranslation(TranslationProvider):
    name = "demo-translation"

    # A tiny, illustrative glossary. NOT a complete translator.
    GLOSSARY = {
        "douleur": "metit",
        "fièvre": "tàngaay",
        "ventre": "biir",
        "tête": "bopp",
        "toux": "sëq",
        "patient": "bóppam / jàngoro",
        "depuis": "ci",
        "jours": "fan",
        "médecin": "doktoor",
        "eau": "ndox",
    }

    def translate(self, text: str, *, source: str, target: str) -> tuple[str, bool]:
        # Word-level illustrative substitution; clearly marked as demo.
        words = re.split(r"(\W+)", text)
        out = []
        for w in words:
            key = w.lower()
            if source.startswith("fr") and target.startswith("wo") and key in self.GLOSSARY:
                out.append(self.GLOSSARY[key])
            else:
                out.append(w)
        return "".join(out), True
