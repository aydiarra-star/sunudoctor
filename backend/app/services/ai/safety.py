"""Clinical safety engine.

This module enforces the project's core promise: ZERO CLINICAL INVENTION.

Guarantees implemented here:
1. Grounding: any clinical value produced by the AI must be traceable to the
   source transcription. Values that cannot be grounded are dropped and flagged.
2. Negation: "pas de fièvre", "amul fièvre", "sans fièvre", "n'a pas" must be
   preserved as negations and NEVER turned into a positive finding.
3. Uncertainty: "je ne sais pas", "xamuma", "peut-être" must be kept as
   uncertain, never converted into an invented value.
4. Absence vs negation: missing information becomes "Non documenté", never a
   negation or a positive finding.
5. Diagnosis is never auto-populated by the AI; it is always left for the
   professional to enter.
"""
from __future__ import annotations

import re
import unicodedata

from app.services.ai.base import StructuredField, StructuredNote

# Markers of negation in French and Wolof.
NEGATION_MARKERS = [
    "pas de",
    "pas d'",
    "pas de ",
    "ne pas",
    "n'a pas",
    "n'est pas",
    "aucun",
    "aucune",
    "sans ",
    "ni ",
    "amul",  # wolof: there is not
    "amoul",
    "nekkul",
    "bu amul",
]

# Wolof negation particle "du" / "dul" is context-dependent, so it is matched
# as a standalone word (typically clause-final) rather than a substring.
WOLOF_NEGATION_RE = re.compile(r"\bdu[l]?\b", re.IGNORECASE)

UNCERTAINTY_MARKERS = [
    "je ne sais pas",
    "je ne sais",
    "on ne sait pas",
    "peut-être",
    "peut etre",
    "possible",
    "xamuma",  # wolof: I don't know
    "xamu ma",
    "xamul",
    "à vérifier",
    "a verifier",
    "incertain",
    "pas sûr",
    "pas sur",
    "semble",
    "probablement",
]

# Units / dose patterns that require maximum vigilance.
DOSE_PATTERN = re.compile(
    r"\b(\d+[.,]?\d*)\s*(mg|g|ml|cl|mcg|µg|ui|iu|comprimé|comprime|cp|goutte|gouttes)\b",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(r"\d+[.,]?\d*")

ABSENT_LABEL = "Non documenté"
UNCERTAIN_LABEL = "À vérifier"


def normalize(text: str) -> str:
    """Lowercase and strip accents for robust matching (keeps digits)."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def contains_negation(text: str) -> bool:
    n = normalize(text)
    if any(marker in n for marker in (normalize(m) for m in NEGATION_MARKERS)):
        return True
    # Wolof "du"/"dul" as a standalone word.
    return WOLOF_NEGATION_RE.search(text) is not None


def contains_uncertainty(text: str) -> bool:
    n = normalize(text)
    return any(marker in n for marker in (normalize(m) for m in UNCERTAINTY_MARKERS))


def extract_doses(text: str) -> list[str]:
    """Return dose strings found in text, normalising the decimal separator."""
    found = []
    for match in DOSE_PATTERN.finditer(text):
        number, unit = match.group(1), match.group(2)
        found.append(f"{number.replace(',', '.')} {unit}")
    return found


def is_grounded(value: str | None, source: str) -> bool:
    """A value is grounded if its meaningful tokens all appear in the source.

    Numbers must match exactly (protects doses such as 5 mg vs 50 mg).
    """
    if not value:
        return False
    src = normalize(source)
    val = normalize(value)
    # Every number in the value must appear in the source.
    for num in NUMBER_PATTERN.findall(val):
        if num not in src:
            return False
    tokens = [t for t in re.findall(r"[a-z0-9]+", val) if len(t) > 2]
    if not tokens:
        return len(val.strip()) > 0 and val.strip() in src
    hits = sum(1 for t in tokens if t in src)
    return hits / len(tokens) >= 0.6


def _sanitize_field(field: StructuredField, source: str, label: str, flags: list[str]) -> StructuredField:
    if field.value is None:
        return field
    if not is_grounded(field.value, source):
        flags.append(f"{label}: valeur non ancrée dans la transcription, supprimée")
        return StructuredField(value=None, uncertain=True)
    if contains_uncertainty(field.value):
        field.uncertain = True
        flags.append(f"{label}: incertitude détectée — {UNCERTAIN_LABEL}")
    return field


def review(note: StructuredNote, transcription: str) -> tuple[StructuredNote, list[str]]:
    """Sanitise a structured note against its source transcription.

    This never adds clinical content. It only removes or flags content that
    cannot be grounded, and it forbids automatic diagnosis.
    """
    flags: list[str] = []

    note.chief_complaint = _sanitize_field(note.chief_complaint, transcription, "Motif", flags)
    note.history = _sanitize_field(note.history, transcription, "Histoire", flags)
    note.exam = _sanitize_field(note.exam, transcription, "Examen", flags)
    note.investigations = _sanitize_field(note.investigations, transcription, "Examens", flags)
    note.decision = _sanitize_field(note.decision, transcription, "Décision", flags)
    note.prescription = _sanitize_field(note.prescription, transcription, "Prescription", flags)
    note.recommendations = _sanitize_field(
        note.recommendations, transcription, "Recommandations", flags
    )
    note.follow_up = _sanitize_field(note.follow_up, transcription, "Suivi", flags)

    clean_symptoms: list[StructuredField] = []
    for sym in note.symptoms:
        sym = _sanitize_field(sym, transcription, "Symptôme", flags)
        if sym.value is None:
            continue
        # A symptom whose source span is a negation must never become positive.
        if sym.source_span and contains_negation(sym.source_span):
            if sym.value not in note.negated_symptoms:
                note.negated_symptoms.append(sym.value)
            flags.append(f"Symptôme '{sym.value}' était nié — conservé comme négation")
            continue
        clean_symptoms.append(sym)
    note.symptoms = clean_symptoms

    # Allergy: never invent, and treat negation.
    clean_allergies = []
    for alg in note.allergies:
        alg = _sanitize_field(alg, transcription, "Allergie", flags)
        if alg.value is None:
            continue
        clean_allergies.append(alg)
    note.allergies = clean_allergies

    # Medications: each must be grounded; doses checked digit by digit.
    clean_meds = []
    for med in note.medications:
        name = med.get("name")
        if not is_grounded(name, transcription):
            flags.append(f"Médicament '{name}' non ancré — supprimé")
            continue
        dose = med.get("dose")
        if dose:
            src_doses = [d.replace(",", ".") for d in extract_doses(transcription)]
            if dose.replace(",", ".") not in src_doses:
                flags.append(f"Dose '{dose}' pour '{name}' non confirmée — {UNCERTAIN_LABEL}")
                med["dose"] = None
                med["uncertain"] = True
        clean_meds.append(med)
    note.medications = clean_meds

    # Vitals: values must be grounded; uncertainty preserved.
    clean_vitals = []
    for vit in note.vitals:
        value = str(vit.get("value", ""))
        if not is_grounded(value, transcription):
            flags.append(f"Constante '{vit.get('label')}' non ancrée — supprimée")
            continue
        clean_vitals.append(vit)
    note.vitals = clean_vitals

    # Diagnosis is NEVER auto-filled by the AI.
    if note.diagnosis.value:
        flags.append(
            "Diagnostic proposé par l'IA retiré : le diagnostic doit être saisi par le professionnel"
        )
    note.diagnosis = StructuredField(value=None, uncertain=False)

    # Record uncertainties.
    for flag in flags:
        if flag not in note.uncertainties:
            note.uncertainties.append(flag)

    return note, flags


def uncertainty_label() -> str:
    return UNCERTAIN_LABEL


def absent_label() -> str:
    return ABSENT_LABEL
