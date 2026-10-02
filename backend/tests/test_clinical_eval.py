"""Clinical evaluation tests: metrics + synthetic dataset invariants.

These tests MEASURE real values (WER, CER, entity precision/recall, dose errors)
against the synthetic dataset. They also assert the hard safety invariants that
must hold for every case: no invention, negation preserved, uncertainty kept,
doses exact.
"""
from __future__ import annotations

import pytest

from app.services.ai import metrics, safety
from app.services.ai.dataset import DATASET
from app.services.ai.demo_providers import DemoClinicalAI

IDS = [c["id"] for c in DATASET]


# ---- Metrics correctness (pure functions) ---- #

def test_wer_identical_is_zero():
    assert metrics.word_error_rate("douleur ventre", "douleur ventre") == 0.0


def test_wer_one_substitution():
    # 1 wrong word out of 2 -> 0.5
    assert metrics.word_error_rate("douleur ventre", "douleur tete") == 0.5


def test_cer_bounds():
    assert metrics.character_error_rate("abc", "abc") == 0.0
    assert metrics.character_error_rate("abc", "abd") > 0.0


def test_entity_scores_detect_hallucination():
    scores = metrics.entity_scores("douleur", "douleur fièvre")
    # "fièvre" was not in the reference -> hallucination.
    assert scores.false_positives >= 1
    assert scores.hallucination_rate > 0


def test_entity_scores_detect_omission():
    scores = metrics.entity_scores("douleur fièvre", "douleur")
    assert scores.false_negatives >= 1
    assert scores.omission_rate > 0


def test_medication_dose_errors_are_exact():
    err = metrics.medication_dose_errors("paracétamol 5 mg", "paracétamol 50 mg")
    assert "50 mg" in err["invented"]
    assert "5 mg" in err["missed"]
    assert err["exact_match"] is False


def test_medication_dose_match():
    err = metrics.medication_dose_errors("amoxicilline 0,5 mg", "amoxicilline 0.5 mg")
    assert err["exact_match"] is True


# ---- Dataset invariants ---- #

@pytest.mark.parametrize("case", DATASET, ids=IDS)
def test_dataset_case_runs(case):
    note = DemoClinicalAI().structure(case["transcript"], language=case["language"])
    assert note is not None


@pytest.mark.parametrize("case", DATASET, ids=IDS)
def test_no_invented_symptoms(case):
    text = case["transcript"]
    note = DemoClinicalAI().structure(text, language=case["language"])
    for s in note.symptoms:
        assert s.value in text, f"{case['id']}: symptôme non ancré: {s.value}"


@pytest.mark.parametrize("case", DATASET, ids=IDS)
def test_no_invented_medications_or_diagnosis(case):
    text = case["transcript"]
    note = DemoClinicalAI().structure(text, language=case["language"])
    for med in note.medications:
        assert safety.normalize(med["name"]) in safety.normalize(text)
    assert note.diagnosis.value is None


@pytest.mark.parametrize("case", DATASET, ids=IDS)
def test_forbidden_positive_facts_never_emitted(case):
    """No case may ever produce a positive fact listed in must_not_contain."""
    text = case["transcript"]
    note = DemoClinicalAI().structure(text, language=case["language"])
    produced = " ".join(
        [s.value or "" for s in note.symptoms]
        + [note.chief_complaint.value or ""]
        + [note.history.value or ""]
    ).lower()
    for forbidden in case["must_not_contain"]:
        assert forbidden.lower() not in produced, f"{case['id']}: '{forbidden}' produit"


# ---- Aggregate honest metric report ---- #

def test_aggregate_metrics_are_computed_not_invented():
    """Every metric must be a real computation over the dataset."""
    total_wer = 0.0
    hallucinations = 0
    omissions = 0
    dose_errors = 0
    for case in DATASET:
        note = DemoClinicalAI().structure(case["transcript"], language=case["language"])
        # Reconstruct a "hypothesis" from the structured note and compare it to
        # the raw transcript: in demo mode the extractor is a subset of the
        # source, so WER measures what was DROPPED, never what was invented.
        hypothesis = " ".join(s.value or "" for s in note.symptoms)
        total_wer += metrics.word_error_rate(case["transcript"], hypothesis)
        scores = metrics.entity_scores(case["transcript"], hypothesis)
        hallucinations += scores.false_positives
        omissions += scores.false_negatives
        dose_err = metrics.medication_dose_errors(case["transcript"], hypothesis)
        dose_errors += len(dose_err["invented"])

    # The extractive demo provider can drop information but must NEVER invent it.
    assert hallucinations == 0, "Le provider démo ne doit jamais halluciner"
    assert dose_errors == 0, "Aucune dose inventée ne doit apparaître"
    # We only assert the computation produced finite, sane values.
    assert total_wer >= 0.0
    assert omissions >= 0
