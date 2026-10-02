"""Pre-production security tests.

Covers authentication hardening, IDOR/permission boundaries, input validation,
and the separation of clinical vs administrative access.
"""
from __future__ import annotations

from app.core.security import create_access_token, create_refresh_token, decode_token

# ---- Token handling ---- #

def test_access_token_cannot_be_used_as_refresh(client, doctor):
    data, _ = doctor
    # A refresh endpoint must reject an access token.
    r = client.post("/api/auth/refresh", json={"refresh_token": data["access_token"]})
    assert r.status_code == 401


def test_refresh_token_cannot_be_used_as_access(client, doctor):
    data, _ = doctor
    r = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {data['refresh_token']}"}
    )
    assert r.status_code == 401


def test_tampered_token_rejected(client, doctor):
    data, _ = doctor
    token = data["access_token"][:-3] + "abc"
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_token_payload_has_type():
    token = create_access_token("user-1", "doctor")
    payload = decode_token(token)
    assert payload["type"] == "access"
    assert payload["sub"] == "user-1"
    assert "exp" in payload
    refresh = create_refresh_token("user-1")
    assert decode_token(refresh)["type"] == "refresh"


# ---- IDOR / permission boundaries ---- #

def test_idor_patient_read_blocked(client, doctor, doctor2, make_patient):
    _, h1 = doctor
    _, h2 = doctor2
    p = make_patient(h1)
    # Doctor 2 has no grant: must be 403, not 404-leaking or 200.
    assert client.get(f"/api/patients/{p['id']}", headers=h2).status_code == 403


def test_idor_consultation_read_blocked(client, doctor, doctor2, make_patient):
    _, h1 = doctor
    _, h2 = doctor2
    p = make_patient(h1)
    cons = client.post(
        "/api/scribe/consultations", json={"patient_id": p["id"]}, headers=h1
    ).json()
    assert (
        client.get(f"/api/scribe/consultations/{cons['id']}", headers=h2).status_code
        == 403
    )


def test_cannot_grant_access_to_patient_without_access(client, doctor, doctor2, make_patient):
    _, h1 = doctor
    _, h2 = doctor2
    p = make_patient(h1)
    r = client.post(
        f"/api/patients/{p['id']}/access?grantee_id={doctor2[0]['user']['id']}&level=view",
        headers=h2,
    )
    assert r.status_code == 403


def test_patient_cannot_create_patient(client, patient_user):
    _, ph = patient_user
    r = client.post(
        "/api/patients", json={"first_name": "X", "last_name": "Y"}, headers=ph
    )
    assert r.status_code == 403


def test_non_admin_cannot_reach_admin_api(client, doctor):
    _, h = doctor
    assert client.get("/api/admin/users", headers=h).status_code == 403
    assert client.get("/api/admin/audit", headers=h).status_code == 403


def test_admin_cannot_read_clinical_without_grant(client, admin, doctor, make_patient):
    _, ah = admin
    _, dh = doctor
    p = make_patient(dh)
    assert client.get(f"/api/patients/{p['id']}", headers=ah).status_code == 403


# ---- Input validation ---- #

def test_oversized_password_field_rejected(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "long@test.sn",
            "password": "x" * 200,
            "full_name": "Long Pass",
            "role": "doctor",
        },
    )
    assert r.status_code == 422


def test_short_password_rejected(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "short@test.sn",
            "password": "short",
            "full_name": "Short Pass",
            "role": "doctor",
        },
    )
    assert r.status_code == 422


def test_invalid_email_rejected(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "StrongPass123!",
            "full_name": "Bad Email",
            "role": "doctor",
        },
    )
    assert r.status_code == 422


def test_invalid_consent_scope_rejected(client, doctor, make_patient):
    _, h = doctor
    p = make_patient(h)
    r = client.post(
        "/api/consents",
        json={"patient_id": p["id"], "scope": "everything", "granted": True},
        headers=h,
    )
    assert r.status_code == 400


def test_break_glass_duration_capped(client, doctor, make_patient):
    _, h = doctor
    p = make_patient(h)
    r = client.post(
        "/api/break-glass",
        json={
            "patient_id": p["id"],
            "reason": "Urgence vitale documentée",
            "duration_minutes": 99999,
        },
        headers=h,
    )
    assert r.status_code == 400


# ---- Security headers ---- #

def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "X-Request-ID" in r.headers


def test_health_does_not_leak_secrets(client):
    body = client.get("/api/health").json()
    assert "secret_key" not in body
    assert "openai_api_key" not in body
