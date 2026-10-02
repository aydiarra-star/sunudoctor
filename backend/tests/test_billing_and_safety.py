"""Billing, consents, break-glass and honesty tests."""
from __future__ import annotations


def test_plans_are_labelled_launch_pricing(client):
    r = client.get("/api/billing/plans")
    assert r.status_code == 200
    body = r.json()
    assert body["label"] == "Tarifs de lancement"
    assert "pas" in body["disclaimer"].lower() or "ne correspondent pas" in body["disclaimer"].lower()
    codes = {p["code"] for p in body["plans"]}
    assert {"doctor", "nurse", "midwife", "community_agent", "hospital_100", "network"} <= codes
    doctor = next(p for p in body["plans"] if p["code"] == "doctor")
    assert doctor["price_fcfa"] == 15000


def test_payments_are_demo_not_real(client, doctor):
    data, h = doctor
    sub = client.post("/api/billing/subscribe", json={"plan_code": "doctor"}, headers=h).json()
    assert sub["status"] == "trial"
    r = client.post(
        "/api/billing/payments",
        json={"subscription_id": sub["id"], "provider": "wave"},
        headers=h,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["is_demo"] is True
    assert "démonstration" in body["message"].lower()


def test_providers_report_connected_false_in_demo(client):
    r = client.get("/api/billing/providers")
    body = r.json()
    assert body["mode"] == "demo"
    assert all(p["connected"] is False for p in body["providers"])


def test_break_glass_requires_reason(client, doctor, make_patient):
    _, h = doctor
    p = make_patient(h)
    r = client.post(
        "/api/break-glass",
        json={"patient_id": p["id"], "reason": "court", "duration_minutes": 60},
        headers=h,
    )
    assert r.status_code == 400


def test_break_glass_is_audited(client, doctor, admin, make_patient):
    _, h = doctor
    _, ah = admin
    p = make_patient(h)
    r = client.post(
        "/api/break-glass",
        json={
            "patient_id": p["id"],
            "reason": "Urgence vitale, patient inconscient",
            "duration_minutes": 30,
        },
        headers=h,
    )
    assert r.status_code == 200
    logs = client.get("/api/admin/audit?action=break_glass", headers=ah).json()
    assert any(e["patient_id"] == p["id"] for e in logs)


def test_consent_scopes(client, doctor, make_patient):
    _, h = doctor
    p = make_patient(h)
    for scope in ["access", "share", "teleconsultation", "audio", "ai", "research"]:
        r = client.post(
            "/api/consents",
            json={"patient_id": p["id"], "scope": scope, "granted": True},
            headers=h,
        )
        assert r.status_code == 201, scope
    bad = client.post(
        "/api/consents",
        json={"patient_id": p["id"], "scope": "invalid", "granted": True},
        headers=h,
    )
    assert bad.status_code == 400


def test_teleconsultation_reports_video_not_configured(client, doctor, make_patient):
    _, h = doctor
    p = make_patient(h)
    r = client.post(
        "/api/teleconsultations",
        json={"patient_id": p["id"]},
        headers=h,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["video_status"] == "configuration_requise"
    assert body["provider"] == "none"


def test_ice_servers_not_configured(client):
    r = client.get("/api/teleconsultations/ice-servers")
    assert r.json()["configured"] is False


def test_admin_config_does_not_expose_secrets(client, admin):
    _, ah = admin
    r = client.get("/api/admin/config", headers=ah)
    assert r.status_code == 200
    assert r.json()["secrets_exposed"] is False
    assert "secret_key" not in r.json()


def test_security_summary(client, admin):
    _, ah = admin
    r = client.get("/api/admin/security/summary", headers=ah)
    assert r.status_code == 200
    assert r.json()["separation_of_duties"] is True
