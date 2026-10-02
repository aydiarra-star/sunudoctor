"""LOT 3 tests: provider selection honesty, MFA enforcement, payment webhooks
(idempotency + signature), and teleconsultation signalling security.
"""
from __future__ import annotations

import hashlib
import hmac
import json

import pyotp

from app.core.config import settings
from app.services.ai import factory

# ---- Provider selection must be honest ---- #

def test_provider_status_reports_not_connected_in_demo():
    status = factory.provider_status()
    assert status["stt"]["connected"] is False
    assert status["clinical_ai"]["connected"] is False
    assert status["safety"]["connected"] is True  # deterministic, always on
    # A reason is always given so the UI can explain what is missing.
    assert status["stt"]["reason"]


def test_meta_exposes_provider_status(client):
    body = client.get("/api/meta").json()
    assert "providers" in body
    assert body["providers"]["clinical_ai"]["connected"] is False
    assert body["capabilities"]["wolof_speech_to_text"] == "non_connecte"


def test_factory_falls_back_to_demo_when_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "clinical_ai_provider", "openai", raising=False)
    monkeypatch.setattr(settings, "openai_api_key", "", raising=False)
    sel = factory.select_clinical_ai_provider()
    assert sel.is_demo is True
    assert "OPENAI_API_KEY" in sel.reason


def test_factory_selects_real_provider_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "clinical_ai_provider", "openai", raising=False)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-not-real", raising=False)
    sel = factory.select_clinical_ai_provider()
    assert sel.is_demo is False
    assert sel.provider.name == "openai-clinical"


# ---- MFA is enforced at login ---- #

def test_mfa_required_when_enabled(client, doctor):
    data, headers = doctor
    # Enable + confirm MFA for the doctor.
    enable = client.post("/api/auth/mfa/enable", headers=headers).json()
    secret = enable["secret"]
    code = pyotp.TOTP(secret).now()
    assert client.post(f"/api/auth/mfa/confirm?code={code}", headers=headers).status_code == 200

    email = data["user"]["email"]
    # Login without a code now fails.
    r = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert r.status_code == 401
    assert "deux facteurs" in r.json()["detail"].lower()

    # Login with a wrong code fails.
    r = client.post(
        "/api/auth/login",
        json={"email": email, "password": "StrongPass123!", "mfa_code": "000000"},
    )
    assert r.status_code == 401

    # Login with the correct code succeeds.
    r = client.post(
        "/api/auth/login",
        json={"email": email, "password": "StrongPass123!", "mfa_code": pyotp.TOTP(secret).now()},
    )
    assert r.status_code == 200

    # Disable MFA again so later tests on the shared fixture are unaffected.
    from app.core.database import SessionLocal
    from app.models.entities import User

    db = SessionLocal()
    u = db.query(User).filter(User.email == email).first()
    u.mfa_enabled = False
    db.commit()
    db.close()


# ---- Payment webhooks: idempotency + signature ---- #

def _subscribe(client, headers):
    return client.post("/api/billing/subscribe", json={"plan_code": "doctor"}, headers=headers).json()


def test_webhook_duplicate_is_ignored(client, doctor):
    _, h = doctor
    sub = _subscribe(client, h)
    pay = client.post(
        "/api/billing/payments",
        json={"subscription_id": sub["id"], "provider": "wave"},
        headers=h,
    ).json()
    event = {"id": "evt-1", "reference": pay["reference"], "status": "success"}
    first = client.post("/api/billing/webhooks/wave", json=event).json()
    assert first["status"] == "processed"
    second = client.post("/api/billing/webhooks/wave", json=event).json()
    assert second["status"] == "duplicate"
    assert second["processed"] is False


def test_webhook_in_demo_never_confirms_real_success(client, doctor):
    _, h = doctor
    sub = _subscribe(client, h)
    pay = client.post(
        "/api/billing/payments",
        json={"subscription_id": sub["id"], "provider": "wave"},
        headers=h,
    ).json()
    event = {"id": "evt-demo", "reference": pay["reference"], "status": "success"}
    result = client.post("/api/billing/webhooks/wave", json=event).json()
    # In demo mode a success webhook cannot produce a real success state.
    assert result["state"] == "pending"


def test_webhook_bad_signature_rejected_in_live(client, doctor, monkeypatch):
    _, h = doctor
    monkeypatch.setattr(settings, "payment_mode", "live", raising=False)
    monkeypatch.setattr(settings, "wave_webhook_secret", "topsecret", raising=False)
    sub = _subscribe(client, h)
    pay = client.post(
        "/api/billing/payments",
        json={"subscription_id": sub["id"], "provider": "wave"},
        headers=h,
    ).json()
    event = {"id": "evt-live-bad", "reference": pay["reference"], "status": "success"}
    result = client.post(
        "/api/billing/webhooks/wave", json=event, headers={"X-Signature": "wrong"}
    ).json()
    assert result["status"] == "rejected"
    assert result["signature_valid"] is False


def test_webhook_valid_signature_processed(client, doctor, monkeypatch):
    _, h = doctor
    monkeypatch.setattr(settings, "payment_mode", "live", raising=False)
    monkeypatch.setattr(settings, "wave_webhook_secret", "topsecret", raising=False)
    sub = _subscribe(client, h)
    pay = client.post(
        "/api/billing/payments",
        json={"subscription_id": sub["id"], "provider": "wave"},
        headers=h,
    ).json()
    event = {"id": "evt-live-ok", "reference": pay["reference"], "status": "success"}
    raw = json.dumps(event).encode()
    sig = hmac.new(b"topsecret", raw, hashlib.sha256).hexdigest()
    result = client.post(
        "/api/billing/webhooks/wave",
        content=raw,
        headers={"X-Signature": sig, "Content-Type": "application/json"},
    ).json()
    assert result["status"] == "processed"
    assert result["signature_valid"] is True
    assert result["state"] == "success"


# ---- Teleconsultation signalling security ---- #

def test_signalling_requires_room_and_participant(client, doctor, doctor2, make_patient):
    _, h = doctor
    _, h2 = doctor2
    p = make_patient(h)
    tele = client.post("/api/teleconsultations", json={"patient_id": p["id"]}, headers=h).json()
    # Cannot post a signal before the room is opened.
    r = client.post(
        f"/api/teleconsultations/{tele['id']}/signal",
        json={"kind": "offer", "payload": {"sdp": "x"}},
        headers=h,
    )
    assert r.status_code == 404
    # Accept opens the room.
    acc = client.post(f"/api/teleconsultations/{tele['id']}/accept", headers=h).json()
    assert acc["room_ref"]
    # Another professional (non participant) cannot post.
    r = client.post(
        f"/api/teleconsultations/{tele['id']}/signal",
        json={"kind": "offer", "payload": {"sdp": "x"}},
        headers=h2,
    )
    assert r.status_code == 403
    # The participant can post.
    r = client.post(
        f"/api/teleconsultations/{tele['id']}/signal",
        json={"kind": "offer", "payload": {"sdp": "x"}},
        headers=h,
    )
    assert r.status_code == 200


def test_ice_servers_report_turn_status(client):
    body = client.get("/api/teleconsultations/ice-servers").json()
    # No TURN configured in tests -> not configured, but STUN is present.
    assert body["configured"] is False
    assert body["turn_configured"] is False
    assert body["ice_servers"]
