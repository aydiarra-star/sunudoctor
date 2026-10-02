"""Anti-hallucination tests for the clinical AI safety engine.

These tests enforce the project's core guarantee: the AI never invents clinical
content, never turns a negation into a positive finding, never turns "I don't
know" into a value, and treats medication numbers with maximum vigilance.
"""
from __future__ import annotations

from app.services.ai import safety
from app.services.ai.base import StructuredField, StructuredNote
from app.services.ai.demo_providers import DemoClinicalAI


# ---- Negation handling ----

def test_pas_de_fievre_is_not_fever():
    note = StructuredNote(
        symptoms=[StructuredField(value="fièvre", source_span="pas de fièvre")],
        chief_complaint=StructuredField(value="pas de fièvre"),
    )
    reviewed, flags = safety.review(note, "pas de fièvre")
    # "fièvre" must never appear as a positive symptom.
    assert all("fièvre" not in (s.value or "") for s in reviewed.symptoms)
    assert any("fièvre" in n for n in reviewed.negated_symptoms)


def test_sans_fievre_preserved_as_negation():
    assert safety.contains_negation("sans fièvre")
    assert safety.contains_negation("aucune allergie")
    assert safety.contains_negation("n'a pas de toux")
    assert safety.contains_negation("fièvre du")  # wolof negation particle


def test_negation_not_flagged_for_positive_sentence():
    assert not safety.contains_negation("le patient a de la fièvre")


# ---- Uncertainty handling ----

def test_je_ne_sais_pas_is_uncertain():
    assert safety.contains_uncertainty("je ne sais pas")
    assert safety.contains_uncertainty("xamuma")
    assert safety.contains_uncertainty("peut-être")


def test_uncertain_value_is_marked_not_invented():
    note = StructuredNote(chief_complaint=StructuredField(value="je ne sais pas la durée"))
    reviewed, _ = safety.review(note, "je ne sais pas la durée")
    assert reviewed.chief_complaint.uncertain is True
    assert reviewed.chief_complaint.value is not None  # preserved, not fabricated


# ---- Grounding: no invented values ----

def test_ungrounded_value_removed():
    note = StructuredNote(chief_complaint=StructuredField(value="douleur thoracique intense"))
    reviewed, flags = safety.review(note, "le patient va bien")
    assert reviewed.chief_complaint.value is None
    assert any("non ancrée" in f for f in flags)


def test_diagnosis_never_auto_filled():
    note = StructuredNote(diagnosis=StructuredField(value="paludisme"))
    reviewed, flags = safety.review(note, "fièvre depuis trois jours, paludisme")
    # Even though the word appears, the AI must not propose a diagnosis.
    assert reviewed.diagnosis.value is None
    assert any("Diagnostic" in f for f in flags)


# ---- Medication / dose vigilance ----

def test_dose_extraction_distinguishes_numbers():
    doses = safety.extract_doses("paracétamol 5 mg, pas 50 mg")
    assert "5 mg" in doses
    assert "50 mg" in doses
    assert "5 mg" != "50 mg"


def test_decimal_dose_normalised():
    assert safety.extract_doses("0,5 mg") == ["0.5 mg"]
    assert safety.extract_doses("5 ml") == ["5 ml"]


def test_invented_dose_removed():
    note = StructuredNote(
        medications=[{"name": "paracétamol", "dose": "50 mg", "uncertain": False}]
    )
    reviewed, flags = safety.review(note, "paracétamol 5 mg")
    med = reviewed.medications[0]
    assert med["dose"] is None  # 50 mg was never said
    assert med["uncertain"] is True
    assert any("Dose" in f for f in flags)


def test_grounded_dose_kept():
    note = StructuredNote(
        medications=[{"name": "paracétamol", "dose": "5 mg", "uncertain": False}]
    )
    reviewed, _ = safety.review(note, "paracétamol 5 mg")
    assert reviewed.medications[0]["dose"] == "5 mg"


def test_invented_medication_removed():
    note = StructuredNote(medications=[{"name": "amoxicilline", "dose": None}])
    reviewed, flags = safety.review(note, "paracétamol 5 mg")
    assert reviewed.medications == []
    assert any("non ancré" in f for f in flags)


# ---- End-to-end demo provider (extractive, cannot invent) ----

def test_demo_provider_wolof_example_preserves_negation():
    text = "Patient bi dafa am douleur ci ventre bi depuis trois days, te fièvre du."
    note = DemoClinicalAI().structure(text, language="wolof")
    # Every produced symptom must be a substring of the source.
    for s in note.symptoms:
        assert s.value in text
    # The negated fever clause must be captured as a negation, never positive.
    assert all("fièvre" not in (s.value or "") for s in note.symptoms)


def test_demo_provider_output_is_always_substring():
    text = "Douleur à la tête depuis deux jours, pas de vomissements."
    note = DemoClinicalAI().structure(text)
    for s in note.symptoms:
        assert s.value in text
    for med in note.medications:
        assert med["name"].lower() in text.lower()


def test_demo_provider_never_creates_diagnosis():
    note = DemoClinicalAI().structure("Fièvre et toux depuis trois jours.")
    assert note.diagnosis.value is None
    assert note.is_demo is True
