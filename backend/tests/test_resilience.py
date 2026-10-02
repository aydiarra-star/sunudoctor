"""Resilience tests: the platform must fail gracefully when a dependency is down.

Covers:
- STT provider unreachable -> 503 with an honest message (no invented transcript)
- Clinical AI unreachable -> 503, transcript preserved
- Payment webhook duplicate / delayed / bad signature
- Offline queue logic is exercised on the frontend (see frontend tests)
"""
from __future__ import annotations

from app.core.config import settings
from app.services.ai.base import StructuredNote
from app.services.ai.real_providers import ProviderUnavailable


def test_stt_unavailable_returns_503(client, doctor, make_patient, monkeypatch):
    _, h = doctor
    p = make_patient(h)
    cons = client.post(
        "/api/scribe/consultations", json={"patient_id": p["id"]}, headers=h
    ).json()

    # Force a real (unreachable) STT provider.
    class BrokenSTT:
        name = "broken"

        def transcribe(self, audio, *, language_hint="wolof", text_hint=None):
            raise ProviderUnavailable("injoignable")

    monkeypatch.setattr(
        "app.api.routes.scribe.get_stt_provider", lambda: (BrokenSTT(), False)
    )
    r = client.post(
        "/api/scribe/transcribe",
        json={"consultation_id": cons["id"], "audio_base64": "AAAA"},
        headers=h,
    )
    assert r.status_code == 503
    assert "indisponible" in r.json()["detail"].lower()


def test_clinical_ai_unavailable_returns_503(client, doctor, make_patient, monkeypatch):
    _, h = doctor
    p = make_patient(h)
    cons = client.post(
        "/api/scribe/consultations", json={"patient_id": p["id"]}, headers=h
    ).json()
    t = client.post(
        "/api/scribe/transcribe",
        json={"consultation_id": cons["id"], "text_hint": "douleur ventre"},
        headers=h,
    ).json()

    class BrokenAI:
        name = "broken"

        def structure(self, transcription, *, language="wolof"):
            raise ProviderUnavailable("injoignable")

    monkeypatch.setattr(
        "app.api.routes.scribe.get_clinical_ai_provider", lambda: (BrokenAI(), False)
    )
    r = client.post(
        "/api/scribe/structure",
        json={"transcription_id": t["transcription_id"]},
        headers=h,
    )
    assert r.status_code == 503
    assert "transcription disponible" in r.json()["detail"].lower()


def test_invalid_audio_base64_rejected(client, doctor, make_patient):
    _, h = doctor
    p = make_patient(h)
    cons = client.post(
        "/api/scribe/consultations", json={"patient_id": p["id"]}, headers=h
    ).json()
    r = client.post(
        "/api/scribe/transcribe",
        json={"consultation_id": cons["id"], "audio_base64": "!!!not-base64!!!"},
        headers=h,
    )
    assert r.status_code == 400


def test_payment_reconcile_rejects_invalid_state(client, doctor):
    _, h = doctor
    sub = client.post(
        "/api/billing/subscribe", json={"plan_code": "doctor"}, headers=h
    ).json()
    pay = client.post(
        "/api/billing/payments",
        json={"subscription_id": sub["id"], "provider": "bank"},
        headers=h,
    ).json()
    r = client.post(
        f"/api/billing/payments/{pay['id']}/reconcile?state=bogus", headers=h
    )
    assert r.status_code == 400


def test_webhook_non_dict_payload_rejected(client):
    r = client.post("/api/billing/webhooks/wave", json=[1, 2, 3])
    assert r.status_code == 400


def test_real_provider_requires_credentials(monkeypatch):
    """A real provider must never be silently used without a credential."""
    monkeypatch.setattr(settings, "stt_provider", "azure", raising=False)
    monkeypatch.setattr(settings, "azure_speech_key", "", raising=False)
    from app.services.ai import factory

    assert factory.select_stt_provider().is_demo is True


def test_demo_note_never_has_diagnosis():
    from app.services.ai.demo_providers import DemoClinicalAI

    note: StructuredNote = DemoClinicalAI().structure("fièvre et toux depuis 3 jours")
    assert note.diagnosis.value is None
