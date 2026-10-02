"""REAL provider adapters.

These classes talk to genuine external services. They are only instantiated when
the operator has configured the matching credentials — see
``app.services.ai.factory``. When a call fails they raise ``ProviderUnavailable``
so the API can return an honest degradation message instead of inventing output.

Hard rules enforced here:
- No credential ever reaches the frontend: every call is server-side.
- The clinical provider is EXTRACTIVE ONLY. Its prompt forbids inventing facts
  and the deterministic safety engine (``app.services.ai.safety``) re-checks
  every returned value against the transcript afterwards. If the model returns
  anything not grounded in the transcript, the safety layer drops it.
- Speech-to-text never fabricates: if the engine returns nothing, the raw text
  is empty and the caller must show "transcription indisponible".
"""
from __future__ import annotations

import json
import logging

import httpx

from app.core.config import settings
from app.services.ai.base import (
    ClinicalAIProvider,
    StructuredField,
    StructuredNote,
    TranscriptionResult,
    TranscriptionSegment,
)

logger = logging.getLogger("sunudoctor.ai")


class ProviderUnavailable(RuntimeError):
    """Raised when a real provider cannot be reached or is misconfigured."""


# --------------------------------------------------------------------------- #
# Speech-to-text (Azure Speech)
# --------------------------------------------------------------------------- #
class AzureSpeechToTextProvider:
    """Real speech-to-text via the Azure Speech REST API.

    Azure Speech supports ``wo-SN`` (Wolof, Senegal) for both transcription and
    language identification, which is why it is the default real STT engine for
    SunuDoctor. The audio is POSTed server-side; the key never leaves the
    backend.
    """

    name = "azure-stt"

    def __init__(self, key: str, region: str, endpoint: str = "") -> None:
        self.key = key
        self.region = region
        self.endpoint = endpoint or f"https://{region}.stt.speech.microsoft.com"

    def _recognize_url(self, language: str) -> str:
        return (
            f"{self.endpoint}/speech/recognition/conversation/cognitiveservices/v1"
            f"?language={language}&profanity=raw"
        )

    def transcribe(
        self,
        audio: bytes | None,
        *,
        language_hint: str = "wolof",
        text_hint: str | None = None,
    ) -> TranscriptionResult:
        # A text hint is an explicit operator input (typed transcript), used by
        # tests and by the "saisie manuelle" path. It is not audio decoding.
        if text_hint and not audio:
            return TranscriptionResult(
                raw_text=text_hint.strip(),
                language=language_hint,
                provider=self.name,
                is_demo=False,
                segments=[],
            )

        if not audio:
            raise ProviderUnavailable("Aucun flux audio fourni au moteur de reconnaissance.")

        language = _azure_language(language_hint)
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
            "Accept": "application/json",
        }
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(self._recognize_url(language), headers=headers, content=audio)
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"Moteur de transcription injoignable : {exc}") from exc

        if resp.status_code >= 400:
            # Never surface the raw provider body (may contain request ids).
            raise ProviderUnavailable(
                f"Moteur de transcription indisponible (HTTP {resp.status_code})."
            )

        payload = resp.json()
        if payload.get("RecognitionStatus") != "Success":
            # A real "no speech recognised" is NOT an invented transcript.
            return TranscriptionResult(
                raw_text="",
                language=language_hint,
                provider=self.name,
                is_demo=False,
                uncertain_spans=["Aucune parole reconnue dans l'audio."],
            )

        text = (payload.get("DisplayText") or "").strip()
        duration = payload.get("Duration")
        duration_s = duration / 10_000_000 if isinstance(duration, int) else None
        segment = TranscriptionSegment(
            start=0.0,
            end=duration_s or 0.0,
            text=text,
            language=language_hint,
            confidence=payload.get("Confidence"),
        )
        return TranscriptionResult(
            raw_text=text,
            language=language_hint,
            provider=self.name,
            is_demo=False,
            segments=[segment] if text else [],
            confidence=payload.get("Confidence"),
            duration_seconds=duration_s,
        )


def _azure_language(hint: str) -> str:
    """Map an internal language hint to an Azure recognition locale."""
    mapping = {
        "wolof": "wo-SN",
        "wo": "wo-SN",
        "français": "fr-FR",
        "fr": "fr-FR",
        "wolof+fr": "wo-SN",
        "wo+fr": "wo-SN",
        "mixed": "wo-SN",
    }
    return mapping.get(hint, settings.stt_default_language)


# --------------------------------------------------------------------------- #
# Clinical structuring (OpenAI-compatible chat completions)
# --------------------------------------------------------------------------- #
STRUCTURING_SYSTEM_PROMPT = """Tu es un assistant de documentation clinique pour un \
professionnel de santé au Sénégal. Tu EXTRAIS uniquement les informations présentes \
dans la transcription fournie. Tu ne dois JAMAIS inventer ni compléter une information.

Règles absolues :
- Si une information est absente, tu ne la produis pas. N'invente aucun symptôme, \
aucun médicament, aucune dose, aucune allergie, aucun antécédent, aucun résultat.
- Si une information est incertaine (doute exprimé), tu la marques "uncertain": true \
et tu conserves le texte source exact.
- Une négation ("pas de fièvre", "fièvre du", "amul", "sans") n'est jamais un symptôme \
positif : mets-la dans "negated_symptoms".
- Tu ne proposes JAMAIS de diagnostic. Le champ "diagnosis" reste null.
- Les nombres et doses doivent être recopiés EXACTEMENT (5 mg ≠ 50 mg).
- Chaque valeur doit être une citation (ou reformulation minimale) du texte source.

Réponds UNIQUEMENT avec un objet JSON valide, sans texte autour, au format :
{
  "chief_complaint": {"value": str|null, "uncertain": bool, "source_span": str|null},
  "history": {"value": str|null, "uncertain": bool, "source_span": str|null},
  "symptoms": [{"value": str, "uncertain": bool, "source_span": str}],
  "negated_symptoms": [str],
  "allergies": [{"value": str, "uncertain": bool, "source_span": str}],
  "medications": [{"name": str, "dose": str|null, "uncertain": bool}],
  "vitals": [{"label": str, "value": str, "unit": str|null}],
  "exam": {"value": str|null, "uncertain": bool, "source_span": str|null},
  "investigations": {"value": str|null, "uncertain": bool, "source_span": str|null},
  "decision": {"value": str|null, "uncertain": bool, "source_span": str|null},
  "prescription": {"value": str|null, "uncertain": bool, "source_span": str|null},
  "recommendations": {"value": str|null, "uncertain": bool, "source_span": str|null},
  "follow_up": {"value": str|null, "uncertain": bool, "source_span": str|null},
  "uncertainties": [str]
}"""


class OpenAIClinicalAIProvider(ClinicalAIProvider):
    """Real clinical structuring through an OpenAI-compatible endpoint.

    The provider is strictly extractive. Even so, its output is passed through
    the deterministic safety engine afterwards, which removes anything that
    cannot be grounded in the source transcript.
    """

    name = "openai-clinical"

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def structure(self, transcription: str, *, language: str = "wolof") -> StructuredNote:
        if not transcription.strip():
            return StructuredNote(provider=self.name, is_demo=False, model=self.model)

        body = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": STRUCTURING_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Langue principale détectée : {language}.\n"
                        f"Transcription :\n\"\"\"\n{transcription}\n\"\"\""
                    ),
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=body
                )
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"Fournisseur d'IA clinique injoignable : {exc}") from exc

        if resp.status_code >= 400:
            raise ProviderUnavailable(
                f"Fournisseur d'IA clinique indisponible (HTTP {resp.status_code})."
            )

        try:
            content = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderUnavailable("Réponse du fournisseur d'IA illisible.") from exc

        return _note_from_dict(data, provider=self.name, model=self.model)


def _field(raw: object) -> StructuredField:
    if not isinstance(raw, dict):
        return StructuredField()
    value = raw.get("value")
    return StructuredField(
        value=value if isinstance(value, str) and value.strip() else None,
        uncertain=bool(raw.get("uncertain", False)),
        source_span=raw.get("source_span") if isinstance(raw.get("source_span"), str) else None,
    )


def _note_from_dict(data: dict, *, provider: str, model: str) -> StructuredNote:
    """Map the model's JSON to a StructuredNote.

    ``diagnosis`` is deliberately never read from the model output: it stays
    empty so the professional is the only source of a diagnosis.
    """
    note = StructuredNote(provider=provider, is_demo=False, model=model)
    note.chief_complaint = _field(data.get("chief_complaint"))
    note.history = _field(data.get("history"))
    note.exam = _field(data.get("exam"))
    note.investigations = _field(data.get("investigations"))
    note.decision = _field(data.get("decision"))
    note.prescription = _field(data.get("prescription"))
    note.recommendations = _field(data.get("recommendations"))
    note.follow_up = _field(data.get("follow_up"))

    for s in data.get("symptoms") or []:
        f = _field(s)
        if f.value:
            note.symptoms.append(f)
    note.negated_symptoms = [str(x) for x in (data.get("negated_symptoms") or []) if x]
    for a in data.get("allergies") or []:
        f = _field(a)
        if f.value:
            note.allergies.append(f)
    for m in data.get("medications") or []:
        if isinstance(m, dict) and m.get("name"):
            note.medications.append(
                {
                    "name": str(m["name"]),
                    "dose": m.get("dose") if isinstance(m.get("dose"), str) else None,
                    "uncertain": bool(m.get("uncertain", False)),
                }
            )
    for v in data.get("vitals") or []:
        if isinstance(v, dict) and v.get("label") and v.get("value") is not None:
            note.vitals.append(
                {
                    "label": str(v["label"]),
                    "value": str(v["value"]),
                    "unit": v.get("unit") if isinstance(v.get("unit"), str) else None,
                }
            )
    note.uncertainties = [str(x) for x in (data.get("uncertainties") or []) if x]
    return note
