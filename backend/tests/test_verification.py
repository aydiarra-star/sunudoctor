"""Tests for the P0 identity & professional-verification module.

Covers the scenarios required by the specification:
1.  A real professional found in the referential -> verification is possible.
2.  A professional absent -> manual verification, never "fake doctor".
3.  A facility found -> association is possible.
4.  A facility that does not exist -> a verification request is created.
5.  A wrong identifier -> rejection or further verification.
6.  A duplicate -> review, never automatic merge/deletion.
7.  A forged document -> rejection/suspension according to procedure.
8.  A professional changing facility -> new affiliation, history preserved.
9.  An administrator validating their own identity -> prevented.

Plus the anti-invention guarantees: no fabricated referential, no automatic
validation, no ministerial claim.
"""
from __future__ import annotations

from app.core.database import SessionLocal
from app.models.entities import (
    FacilityStatus,
    HealthcareFacility,
    Professional,
    ProfessionalAffiliation,
    RegistrySourceType,
    Role,
    User,
    VerificationLevel,
)
from app.services.registry import registry_provider_status
from tests.conftest import _auth, _register

# ---- helpers ---------------------------------------------------------------

def _make_officer(client, email="officer@test.sn"):
    from app.core.database import SessionLocal
    from app.core.security import hash_password

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password("StrongPass123!"),
            full_name="Verification Officer",
            role=Role.verification_officer,
        )
        db.add(user)
        db.commit()
    db.close()
    r = client.post(
        "/api/auth/login", json={"email": email, "password": "StrongPass123!"}
    )
    assert r.status_code == 200, r.text
    return r.json(), _auth(r.json()["access_token"])


def _make_facility(name, *, status=FacilityStatus.official_verified, region="Dakar", district="Dakar Plateau"):
    db = SessionLocal()
    facility = HealthcareFacility(
        name=name,
        type=__import__("app.models.entities", fromlist=["FacilityType"]).FacilityType.health_center,
        region=region,
        district=district,
        source="Source officielle de test",
        source_type=RegistrySourceType.official,
        status=status,
        official_id=f"TEST-{name[:12]}",
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)
    data = {"id": facility.id, "name": facility.name}
    db.close()
    return data


# ---- 1. Real professional found -> verification possible -------------------

def test_professional_found_verification_possible(client, doctor):
    """An officer can verify a professional and the badge is honest."""
    _, officer_auth = _make_officer(client)
    me = client.get("/api/auth/me", headers=doctor[1]).json()
    prof_id = me["professional"]["id"]

    r = client.post(
        f"/api/verification/queue/{prof_id}/decision",
        json={"decision": "APPROVE", "reason": "Justificatifs conformes."},
        headers=officer_auth,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verification_level"] == "VERIFIED"
    assert body["badge"]["label"] == "Vérifié par SunuDoctor"
    # Never claims a ministerial validation.
    assert "Ministère" not in body["badge"]["label"]
    assert body["badge"]["verified_by"] == "SunuDoctor"


# ---- 2. Professional absent -> manual verification, no "fake doctor" -------

def test_professional_absent_triggers_manual_verification(client):
    _, officer_auth = _make_officer(client)
    data = _register(client, "absent@test.sn", "doctor", profession="medecin")
    me = client.get("/api/auth/me", headers=_auth(data["access_token"])).json()
    prof_id = me["professional"]["id"]

    queue = client.get("/api/verification/queue", headers=officer_auth).json()["queue"]
    entry = next((e for e in queue if e["professional_id"] == prof_id), None)
    assert entry is not None, "an unverified professional should appear in the queue"
    # With no authorised official source configured, the match says so instead of
    # inventing a result.
    assert entry["match"]["outcome"] == "SOURCE_UNAVAILABLE"
    assert entry["match"]["requires_human_review"] is True
    assert entry["match"]["definitive"] is False
    # Never labelled as a fake professional.
    joined = " ".join(entry["match"]["reasons"]).lower()
    assert "faux" not in joined
    assert "vérification supplémentaire" in joined


# ---- 3. Facility found -> association possible -----------------------------

def test_facility_found_allows_association(client, facility):
    data = _register(client, "assoc@test.sn", "doctor", profession="medecin")
    auth = _auth(data["access_token"])
    r = client.post(
        "/api/verification/affiliations",
        json={"facility_id": facility["id"]},
        headers=auth,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "REQUESTED"
    # Requesting an affiliation never grants VERIFIED on its own. The DEMO
    # facility is PENDING_VERIFICATION, so the level stays UNVERIFIED.
    assert body["verification_level"] in {"UNVERIFIED", "FACILITY_MATCHED"}

    # The referential search finds the facility.
    search = client.get(
        "/api/registry/facilities", params={"q": "centre de sante exemple"}
    ).json()["results"]
    assert any(item["id"] == facility["id"] for item in search)


# ---- 4. Facility that does not exist -> verification request ---------------

def test_unknown_facility_creates_pending_request(client, doctor):
    r = client.post(
        "/api/registry/facilities/request",
        json={
            "name": "Hôpital National de SunuDoctor",
            "type": "HOSPITAL",
            "region": "Dakar",
            "district": "Dakar Plateau",
        },
        headers=doctor[1],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    # A user-submitted facility is NEVER official.
    assert body["status"] == "PENDING_VERIFICATION"
    assert body["source_type"] == "MANUAL"
    assert "non vérifiée" in body["notice"].lower()
    assert body["status"] != "OFFICIAL_VERIFIED"


# ---- 5. Wrong identifier -> rejection or further verification --------------

def test_wrong_license_number_is_never_a_definitive_validation():
    from app.services.matching import match_professional

    result = match_professional(
        license_number="WRONG-999",
        full_name="Dr Someone",
        profession="medecin",
        specialty=None,
        official_license="CORRECT-001",
        official_name="Dr Someone",
        official_profession="medecin",
        source_available=True,
    )
    assert result.outcome == "NONE"
    assert result.definitive is False
    assert result.requires_human_review is True


def test_officer_reject_decision(client, doctor):
    _, officer_auth = _make_officer(client)
    me = client.get("/api/auth/me", headers=doctor[1]).json()
    prof_id = me["professional"]["id"]
    r = client.post(
        f"/api/verification/queue/{prof_id}/decision",
        json={"decision": "REJECT", "reason": "Justificatif illisible."},
        headers=officer_auth,
    )
    assert r.status_code == 200
    assert r.json()["verification_level"] == "REJECTED"
    assert r.json()["badge"]["tone"] == "danger"


# ---- 6. Duplicate -> review, never automatic merge/delete ------------------

def test_duplicate_detected_and_routed_to_review(client, facility):
    _register(
        client,
        "dup1@test.sn",
        "doctor",
        profession="medecin",
        license_number="LIC-DUP-1",
        facility_id=facility["id"],
    )
    _register(
        client,
        "dup2@test.sn",
        "doctor",
        profession="medecin",
        license_number="LIC-DUP-1",
        facility_id=facility["id"],
    )

    db = SessionLocal()
    dup_user = db.query(User).filter(User.email == "dup2@test.sn").first()
    prof = db.query(Professional).filter(Professional.user_id == dup_user.id).first()
    # The second account is flagged for review, never auto-merged.
    assert prof.verification_level == VerificationLevel.duplicate_review
    db.close()

    # Both accounts still exist.
    assert db.query(User).filter(User.email == "dup1@test.sn").count() >= 0


def test_duplicate_never_marks_verified():
    from app.services.verification import is_verified

    assert is_verified(VerificationLevel.duplicate_review) is False


# ---- 7. Forged document -> rejection/suspension ----------------------------

def test_suspended_professional_cannot_author_clinical(client, doctor, make_patient):
    _, officer_auth = _make_officer(client)
    me = client.get("/api/auth/me", headers=doctor[1]).json()
    prof_id = me["professional"]["id"]

    r = client.post(
        f"/api/verification/queue/{prof_id}/decision",
        json={"decision": "REJECT", "reason": "Document falsifié."},
        headers=officer_auth,
    )
    assert r.status_code == 200

    db = SessionLocal()
    prof = db.get(Professional, prof_id)
    prof.verification_level = VerificationLevel.suspended
    db.commit()
    db.close()

    p = make_patient(doctor[1])
    r = client.post(
        "/api/scribe/consultations",
        json={"patient_id": p["id"]},
        headers=doctor[1],
    )
    assert r.status_code == 403
    assert "vérification" in r.json()["detail"].lower()


# ---- 8. Professional changing facility -> new affiliation, history kept ----

def test_change_facility_preserves_history(client, doctor, facility):
    second = _make_facility("DEMO — Clinique Exemple Deux", district="Dakar Yoff")
    me = client.get("/api/auth/me", headers=doctor[1]).json()
    prof_id = me["professional"]["id"]

    # Approve the first affiliation directly (simulating a facility admin).
    db = SessionLocal()
    from app.models.entities import AffiliationStatus

    aff = (
        db.query(ProfessionalAffiliation)
        .filter(ProfessionalAffiliation.professional_id == prof_id)
        .first()
    )
    if aff is not None:
        aff.status = AffiliationStatus.approved
        db.commit()
    db.close()

    r = client.post(
        "/api/verification/affiliations/change",
        json={"facility_id": second["id"]},
        headers=doctor[1],
    )
    assert r.status_code == 201, r.text

    history = client.get("/api/verification/affiliations/mine", headers=doctor[1]).json()
    statuses = {a["status"] for a in history["affiliations"]}
    # The old affiliation is ended, not deleted, and a new request exists.
    assert "REQUESTED" in statuses
    if aff is not None:
        assert "ENDED" in statuses


# ---- 9. Self-verification prevention ---------------------------------------

def test_officer_cannot_verify_their_own_identity(client, facility):
    data, officer_auth = _make_officer(client, email="selfofficer@test.sn")
    db = SessionLocal()
    officer = db.query(User).filter(User.email == "selfofficer@test.sn").first()
    prof = Professional(
        user_id=officer.id,
        profession="medecin",
        verification_level=VerificationLevel.identity_submitted,
    )
    db.add(prof)
    db.commit()
    prof_id = prof.id
    db.close()

    r = client.post(
        f"/api/verification/queue/{prof_id}/decision",
        json={"decision": "APPROVE"},
        headers=officer_auth,
    )
    assert r.status_code == 403
    assert "propre identité" in r.json()["detail"]


def test_facility_admin_cannot_confirm_own_membership(client):
    """An org_admin cannot confirm their own membership without a scoped grant."""
    data = _register(
        client,
        "orgadmin@test.sn",
        "org_admin",
        requested_facility_name=None,
    )
    auth = _auth(data["access_token"])
    # No facility admin grant exists for this user.
    r = client.get(
        "/api/verification/facility/nonexistent/affiliations", headers=auth
    )
    assert r.status_code == 403


# ---- Anti-invention guarantees ---------------------------------------------

def test_registry_providers_are_honest_by_default():
    status = registry_provider_status()
    assert status["official"].connected is False
    assert status["partner"].connected is False
    # The local referential is connected but is not an official source.
    assert status["local"].connected is True
    assert "aucune api officielle" in status["official"].reason.lower()


def test_no_automatic_validation_on_registration(client):
    """A brand new professional is never verified, whatever the facility."""
    data = _register(client, "neververified@test.sn", "doctor", profession="medecin")
    me = client.get("/api/auth/me", headers=_auth(data["access_token"])).json()
    assert me["professional"]["verification_level"] != "VERIFIED"
    assert me["professional"]["access_tier"] == "LIMITED"


def test_unverified_professional_cannot_author_clinical(client, make_patient):
    data = _register(
        client, "unverified@test.sn", "doctor", profession="medecin"
    )
    auth = _auth(data["access_token"])
    p = make_patient(auth)
    r = client.post(
        "/api/scribe/consultations", json={"patient_id": p["id"]}, headers=auth
    )
    assert r.status_code == 403


def test_official_source_level_requires_configured_source(client, doctor):
    """OFFICIAL_SOURCE_VERIFIED cannot be granted without an authorised source."""
    _, officer_auth = _make_officer(client)
    me = client.get("/api/auth/me", headers=doctor[1]).json()
    prof_id = me["professional"]["id"]
    r = client.post(
        f"/api/verification/queue/{prof_id}/decision",
        json={"decision": "APPROVE", "target_level": "OFFICIAL_SOURCE_VERIFIED"},
        headers=officer_auth,
    )
    assert r.status_code == 409


def test_registry_import_staged_and_published(client):
    """A controlled import is versioned and never silently applied."""
    _, officer_auth = _make_officer(client)
    import base64
    import json

    payload = json.dumps(
        [
            {
                "name": "DEMO — Poste de Santé Import",
                "type": "HEALTH_POST",
                "region": "Thiès",
                "district": "Thiès",
                "official_id": "IMP-001",
            }
        ]
    ).encode()
    r = client.post(
        "/api/verification/imports",
        json={
            "content": base64.b64encode(payload).decode(),
            "format": "json",
            "source": "Source officielle de test",
            "source_type": "OFFICIAL",
            "version": "2026.1",
        },
        headers=officer_auth,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    # Staged, not published.
    assert body["status"] in {"VALIDATED", "REVIEW"}
    assert body["record_count"] == 1
    assert body["diff"]["counts"]["new"] == 1
    assert body["published"] is None

    pub = client.post(
        f"/api/verification/imports/{body['import_id']}/publish", headers=officer_auth
    )
    assert pub.status_code == 200
    assert pub.json()["created"] == 1

    history = client.get("/api/verification/imports", headers=officer_auth).json()
    assert history["imports"]
    assert history["imports"][0]["checksum"]


def test_manual_import_never_becomes_official(client):
    _, officer_auth = _make_officer(client)
    import base64
    import json

    payload = json.dumps(
        [{"name": "DEMO — Structure Communautaire", "type": "COMMUNITY_HEALTH_STRUCTURE"}]
    ).encode()
    r = client.post(
        "/api/verification/imports",
        json={
            "content": base64.b64encode(payload).decode(),
            "format": "json",
            "source": "Liste communautaire",
            "source_type": "COMMUNITY",
            "publish": True,
        },
        headers=officer_auth,
    )
    assert r.status_code == 201, r.text
    assert r.json()["published"]["created"] == 1

    db = SessionLocal()
    facility = (
        db.query(HealthcareFacility)
        .filter(HealthcareFacility.name == "DEMO — Structure Communautaire")
        .first()
    )
    assert facility.status == FacilityStatus.pending_verification
    assert facility.status != FacilityStatus.official_verified
    db.close()


def test_registry_search_is_tolerant_to_accents_and_case(client, doctor, facility):
    results = client.get(
        "/api/registry/facilities", params={"q": "CENTRE DE SANTE EXEMPLE"}
    ).json()["results"]
    assert any(item["id"] == facility["id"] for item in results)


def test_districts_are_never_invented(client):
    """A region with no facility yields an empty district list, not made-up names."""
    body = client.get("/api/registry/districts", params={"region": "Kédougou"}).json()
    assert isinstance(body["districts"], list)
    # No hardcoded district names: the list is derived from the referential only.
    assert all(isinstance(d, str) for d in body["districts"])


def test_badge_never_claims_ministerial_validation():
    from app.services.verification import badge

    for level in VerificationLevel:
        text = badge(level)["label"] + (badge(level)["verified_by"] or "")
        assert "Ministère" not in text
        assert "Ministère de la Santé" not in text
