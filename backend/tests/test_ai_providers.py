"""Tests for the language-detection and AI-validation providers.

These providers must be honest and non-inventive:
- detection reports the language mix without rewriting the transcript;
- validation only reports issues, never edits or completes clinical content.
"""
from __future__ import annotations

from app.services.ai.base import StructuredField, StructuredNote
from app.services.ai.demo_providers import DemoAIValidation, DemoLanguageDetection


def test_detection_wolof_french_mix():
    text = "Patient bi dafa am douleur ci ventre bi depuis trois days, te fièvre du."
    d = DemoLanguageDetection().detect(text)
    assert d.is_demo is True
    assert "wolof" in d.languages
    assert d.primary in {"wolof", "français"}
    # Code-switching must be surfaced, not silently collapsed.
    assert d.mixed is True


def test_detection_never_rewrites_input():
    text = "Patient bi dafa am douleur"
    # Detection is read-only: the same input yields a stable result.
    first = DemoLanguageDetection().detect(text)
    second = DemoLanguageDetection().detect(text)
    assert first.languages == second.languages
    assert first.primary == second.primary


def test_detection_confidence_is_bounded():
    d = DemoLanguageDetection().detect("douleur fièvre toux depuis patient")
    assert 0.0 <= d.confidence <= 1.0


def test_validation_flags_missing_complaint_and_human_diagnosis():
    note = StructuredNote(chief_complaint=StructuredField(value=None))
    result = DemoAIValidation().validate(note, "texte quelconque")
    codes = {i.code for i in result.issues}
    assert "missing" in codes
    assert "human_required" in codes
    assert result.ok is False


def test_validation_does_not_add_content():
    note = StructuredNote(chief_complaint=StructuredField(value="Douleur abdominale"))
    before = note.to_dict()
    DemoAIValidation().validate(note, "Douleur abdominale")
    assert note.to_dict() == before  # validation never mutates the note
    # No diagnosis is ever filled in by validation.
    assert note.diagnosis.value is None
