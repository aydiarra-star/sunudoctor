"""Pytest fixtures. Uses a throwaway SQLite database per test session."""
from __future__ import annotations

import os
import tempfile

# Configure a temporary database BEFORE importing the app.
_tmp_db = os.path.join(tempfile.mkdtemp(), "test_sunudoctor.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["AI_MODE"] = "demo"
os.environ["PAYMENT_MODE"] = "demo"
os.environ["RATE_LIMIT_REQUESTS"] = "100000"

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _register(client, email, role, **extra):
    payload = {
        "email": email,
        "password": "StrongPass123!",
        "full_name": f"Test {role}",
        "role": role,
        **extra,
    }
    # Professional registration requires a facility reference. Tests use an
    # explicitly unverified request so no facility is ever treated as official.
    if role in {
        "doctor",
        "nurse",
        "midwife",
        "other_professional",
        "community_agent",
        "social_worker",
    } and "facility_id" not in payload and "requested_facility_name" not in payload:
        payload["requested_facility_name"] = "DEMO — Structure de test"
    r = client.post("/api/auth/register", json=payload)
    if r.status_code == 409:
        # Already registered by a previous test: log in instead.
        r = client.post(
            "/api/auth/login", json={"email": email, "password": "StrongPass123!"}
        )
    assert r.status_code in (200, 201), r.text
    return r.json()


def promote_verified(email: str) -> None:
    """Mark a test professional as verified.

    Real verification is a human decision; tests that exercise clinical authoring
    need a verified professional, so this simulates the outcome of that decision
    directly in the database.
    """
    from app.core.database import SessionLocal
    from app.models.entities import Professional, User, VerificationLevel

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if prof:
            prof.verification_level = VerificationLevel.verified
            db.commit()
    db.close()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def facility(client):
    """A synthetic, clearly-labelled DEMO facility in the referential."""
    from app.core.database import SessionLocal
    from app.models.entities import (
        FacilityStatus,
        FacilityType,
        HealthcareFacility,
        RegistrySourceType,
    )

    db = SessionLocal()
    existing = (
        db.query(HealthcareFacility)
        .filter(HealthcareFacility.name == "DEMO — Centre de Santé Exemple")
        .first()
    )
    if existing is None:
        existing = HealthcareFacility(
            name="DEMO — Centre de Santé Exemple",
            short_name="DEMO Centre Exemple",
            type=FacilityType.health_center,
            region="Dakar",
            district="Dakar Plateau",
            commune="Plateau",
            source="Jeu de démonstration SunuDoctor",
            source_type=RegistrySourceType.manual,
            status=FacilityStatus.pending_verification,
            is_demo=True,
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
    data = {"id": existing.id, "name": existing.name}
    db.close()
    return data


@pytest.fixture()
def doctor(client):
    data = _register(client, "doctor@test.sn", "doctor", profession="medecin")
    promote_verified("doctor@test.sn")
    return data, _auth(data["access_token"])


@pytest.fixture()
def doctor2(client):
    data = _register(client, "doctor2@test.sn", "doctor", profession="medecin")
    promote_verified("doctor2@test.sn")
    return data, _auth(data["access_token"])


@pytest.fixture()
def nurse(client):
    data = _register(client, "nurse@test.sn", "nurse", profession="infirmier")
    promote_verified("nurse@test.sn")
    return data, _auth(data["access_token"])


@pytest.fixture()
def patient_user(client):
    data = _register(client, "patient@test.sn", "patient")
    return data, _auth(data["access_token"])


@pytest.fixture()
def admin(client):
    # platform_admin is not self-registerable; create directly.
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.entities import Role, User

    db = SessionLocal()
    u = db.query(User).filter(User.email == "admin@test.sn").first()
    if u is None:
        u = User(
            email="admin@test.sn",
            hashed_password=hash_password("StrongPass123!"),
            full_name="Platform Admin",
            role=Role.platform_admin,
        )
        db.add(u)
        db.commit()
    db.close()
    r = client.post(
        "/api/auth/login", json={"email": "admin@test.sn", "password": "StrongPass123!"}
    )
    assert r.status_code == 200, r.text
    return r.json(), _auth(r.json()["access_token"])


@pytest.fixture()
def make_patient(client):
    def _make(auth_headers, first="Demo", last="Patient"):
        r = client.post(
            "/api/patients",
            json={"first_name": first, "last_name": last},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _make
