"""Authentication and RBAC tests."""
from __future__ import annotations


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_meta_is_honest_about_demo(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["ai_mode"] == "demo"
    assert body["demo_banner"] == "Mode démonstration"
    assert body["capabilities"]["wolof_speech_to_text"] == "non_connecte"
    assert body["capabilities"]["teleconsultation_video"] == "configuration_requise"


def test_register_login_and_me(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "a@test.sn",
            "password": "StrongPass123!",
            "full_name": "A B",
            "role": "nurse",
            "profession": "infirmier",
        },
    )
    assert r.status_code == 201
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "nurse"
    # New professional is NOT auto-verified.
    assert me.json()["professional"]["verification_status"] == "pending"


def test_duplicate_email_rejected(client, doctor):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "doctor@test.sn",
            "password": "StrongPass123!",
            "full_name": "Dup",
            "role": "doctor",
        },
    )
    assert r.status_code == 409


def test_invalid_login(client, doctor):
    r = client.post("/api/auth/login", json={"email": "doctor@test.sn", "password": "wrong"})
    assert r.status_code == 401


def test_platform_admin_not_self_registerable(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "hack@test.sn",
            "password": "StrongPass123!",
            "full_name": "Hack",
            "role": "platform_admin",
        },
    )
    assert r.status_code == 400


def test_unauthenticated_patient_list_denied(client):
    r = client.get("/api/patients")
    assert r.status_code == 401


def test_patient_scoped_access_denied_across_professionals(client, doctor, doctor2, make_patient):
    _, h1 = doctor
    _, h2 = doctor2
    p = make_patient(h1)
    # Doctor 2 has no grant for this patient.
    r = client.get(f"/api/patients/{p['id']}", headers=h2)
    assert r.status_code == 403


def test_admin_does_not_automatically_access_clinical_records(
    client, admin, doctor, make_patient
):
    _, admin_h = admin
    _, doc_h = doctor
    p = make_patient(doc_h)
    # Admin can list users...
    assert client.get("/api/admin/users", headers=admin_h).status_code == 200
    # ...but cannot read the clinical record without an explicit grant.
    r = client.get(f"/api/patients/{p['id']}", headers=admin_h)
    assert r.status_code == 403


def test_patient_creation_audited(client, admin, doctor, make_patient):
    _, admin_h = admin
    _, doc_h = doctor
    p = make_patient(doc_h)
    logs = client.get("/api/admin/audit?action=patient_create", headers=admin_h)
    assert logs.status_code == 200
    entries = logs.json()
    assert any(e["patient_id"] == p["id"] for e in entries)
