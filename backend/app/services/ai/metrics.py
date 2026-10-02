"""Clinical AI evaluation metrics.

Computes the metrics the project promises to MEASURE (never to invent):
- WER  : word error rate between a reference and a hypothesis transcript
- CER  : character error rate
- entity precision / recall : how many clinical entities were correctly found
- omission rate : entities present in the reference but missed
- hallucination rate : entities produced that are NOT in the reference
- medication / dose error rate : wrong or invented drug numbers

These functions are pure and dependency-free so they can be unit-tested and
reported honestly. No metric is ever published without a real measurement.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _normalize(text))


def _edit_distance(a: list, b: list) -> int:
    """Levenshtein distance over arbitrary sequences."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref, hyp = _tokens(reference), _tokens(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return round(_edit_distance(ref, hyp) / len(ref), 4)


def character_error_rate(reference: str, hypothesis: str) -> float:
    ref, hyp = list(_normalize(reference)), list(_normalize(hypothesis))
    if not ref:
        return 0.0 if not hyp else 1.0
    return round(_edit_distance(ref, hyp) / len(ref), 4)


# --- Clinical entity extraction (deterministic, for evaluation only) -------- #
SYMPTOM_TERMS = {
    "douleur", "fièvre", "fievre", "toux", "vomissement", "vomissements",
    "diarrhée", "diarrhee", "fatigue", "vertige", "frisson", "frissons",
    "nausée", "nausee", "saignement", "essoufflement", "metit", "biir",
}
MED_TERMS = {
    "paracétamol", "paracetamol", "amoxicilline", "ibuprofène", "ibuprofene",
    "aspirine", "metformine", "amlodipine", "chloroquine", "artéméther",
}
DOSE_RE = re.compile(
    r"\b(\d+[.,]?\d*)\s*(mg|g|ml|cl|mcg|µg|ui|iu|cp|comprimé|comprime)\b",
    re.IGNORECASE,
)


def extract_entities(text: str) -> dict[str, set[str]]:
    norm = _normalize(text)
    tokens = set(re.findall(r"[a-zà-ÿ]+", norm))
    return {
        "symptoms": {s for s in SYMPTOM_TERMS if _normalize(s) in tokens},
        "medications": {m for m in MED_TERMS if _normalize(m) in tokens},
        "doses": {f"{n.replace(',', '.')} {u}" for n, u in DOSE_RE.findall(text)},
    }


@dataclass
class EntityScores:
    precision: float
    recall: float
    omission_rate: float
    hallucination_rate: float
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    extra: dict = field(default_factory=dict)


def entity_scores(reference: str, hypothesis: str) -> EntityScores:
    ref = extract_entities(reference)
    hyp = extract_entities(hypothesis)
    tp = fp = fn = 0
    for kind in ref:
        r, h = ref[kind], hyp[kind]
        tp += len(r & h)
        fp += len(h - r)
        fn += len(r - h)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    total_ref = tp + fn
    return EntityScores(
        precision=round(precision, 4),
        recall=round(recall, 4),
        omission_rate=round(fn / total_ref, 4) if total_ref else 0.0,
        hallucination_rate=round(fp / (tp + fp), 4) if (tp + fp) else 0.0,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
    )


def medication_dose_errors(reference: str, hypothesis: str) -> dict:
    """Count dose mismatches: wrong numbers are the most dangerous error."""
    ref_doses = extract_entities(reference)["doses"]
    hyp_doses = extract_entities(hypothesis)["doses"]
    return {
        "reference_doses": sorted(ref_doses),
        "hypothesis_doses": sorted(hyp_doses),
        "invented": sorted(hyp_doses - ref_doses),
        "missed": sorted(ref_doses - hyp_doses),
        "exact_match": ref_doses == hyp_doses,
    }
