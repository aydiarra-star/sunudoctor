"""Wolof / French evaluation suite.

Runs every documented case from app.services.ai.eval_cases against the
structuring + safety pipeline and asserts the invariants that must always hold,
regardless of language: no invention, negation preserved, uncertainty preserved,
numbers exact.
"""
from __future__ import annotations

import pytest

from app.services.ai import safety
from app.services.ai.demo_providers import DemoClinicalAI
from app.services.ai.eval_cases import CASES


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case_runs_without_error(case):
    note = DemoClinicalAI().structure(case["input"], language=case["language"])
    assert note is not None


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_no_invention_generic_invariants(case):
    text = case["input"]
    note = DemoClinicalAI().structure(text, language=case["language"])
    # 1. Every symptom value must be grounded in the source.
    for s in note.symptoms:
        assert s.value in text, f"{case['id']}: symptôme non ancré: {s.value}"
    # 2. Every medication name must be grounded (accent-insensitive).
    for med in note.medications:
        assert safety.normalize(med["name"]) in safety.normalize(text), (
            f"{case['id']}: médicament inventé"
        )
    # 3. No diagnosis is ever produced by the AI.
    assert note.diagnosis.value is None, f"{case['id']}: diagnostic inventé"
    # 4. Every vital value must be grounded.
    for vit in note.vitals:
        assert str(vit["value"]) in text, f"{case['id']}: constante non ancrée"


def test_wolof_fever_negation_case():
    case = next(c for c in CASES if c["id"] == "wo-001")
    note = DemoClinicalAI().structure(case["input"])
    assert all("fièvre" not in (s.value or "") for s in note.symptoms)


def test_french_negation_case():
    case = next(c for c in CASES if c["id"] == "fr-002")
    text = case["input"]
    note = DemoClinicalAI().structure(text)
    assert all("vomissement" not in (s.value or "") for s in note.symptoms)


def test_uncertainty_case_preserved():
    case = next(c for c in CASES if c["id"] == "wo-003")
    note = DemoClinicalAI().structure(case["input"])
    assert note.uncertainties, "L'incertitude doit être conservée"


def test_medication_numbers_not_confused():
    assert safety.extract_doses("5 mg") != safety.extract_doses("50 mg")
    assert safety.extract_doses("0,5 mg") == ["0.5 mg"]


def test_accent_normalisation():
    assert safety.normalize("Fièvre") == safety.normalize("fievre")
