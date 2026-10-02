"""End-to-end scribe pipeline: PARLER -> TRANSCRIRE -> STRUCTURER -> VERIFIER -> VALIDER."""
from __future__ import annotations


def _consultation(client, headers, patient_id, complaint=None):
    r = client.post(
        "/api/scribe/consultations",
        json={"patient_id": patient_id, "chief_complaint": complaint},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_full_pipeline(client, doctor, make_patient):
    _, h = doctor
    patient = make_patient(h, first="Demo", last="Scribe")
    cons = _consultation(client, h, patient["id"])

    # Transcribe (demo mode uses a typed text hint; no real STT configured).
    text = "Patient bi dafa am douleur ci ventre bi depuis trois days, te fièvre du."
    r = client.post(
        "/api/scribe/transcribe",
        json={
            "consultation_id": cons["id"],
            "language_hint": "wolof",
            "text_hint": text,
            "consent_audio": False,
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_demo"] is True
    assert body["demo_banner"] == "Mode démonstration"
    assert body["raw_text"] == text

    # Structure.
    r = client.post(
        "/api/scribe/structure",
        json={"transcription_id": body["transcription_id"]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    structured = r.json()
    assert structured["status"] == "draft_ai"
    assert structured["is_demo"] is True
    assert "vérifiez son exactitude" in structured["disclaimer"].lower()

    # Validate (only a human can).
    r = client.post(
        f"/api/scribe/consultations/{cons['id']}/validate",
        json={"decision": "Réévaluation à 48h", "change_note": "Validation médecin"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "validated"
    assert r.json()["validated_by"] == doctor[0]["user"]["id"]

    # History must show the version.
    r = client.get(f"/api/scribe/consultations/{cons['id']}/history", headers=h)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_patient_cannot_validate(client, doctor, patient_user, make_patient):
    _, h = doctor
    _, ph = patient_user
    patient = make_patient(h)
    cons = _consultation(client, h, patient["id"])
    r = client.post(
        f"/api/scribe/consultations/{cons['id']}/validate", json={}, headers=ph
    )
    assert r.status_code == 403


def test_ai_never_returns_a_diagnosis(client, doctor, make_patient):
    _, h = doctor
    patient = make_patient(h)
    cons = _consultation(client, h, patient["id"])
    t = client.post(
        "/api/scribe/transcribe",
        json={"consultation_id": cons["id"], "text_hint": "fièvre, paludisme suspecté"},
        headers=h,
    ).json()
    s = client.post(
        "/api/scribe/structure", json={"transcription_id": t["transcription_id"]}, headers=h
    ).json()
    assert s["structured"]["diagnosis"]["value"] is None


def test_wolof_eval_endpoint(client):
    r = client.get("/api/scribe/wolof-eval")
    assert r.status_code == 200
    assert r.json()["count"] >= 10


def test_transcribe_without_consent_does_not_retain_audio(client, doctor, make_patient):
    _, h = doctor
    patient = make_patient(h)
    cons = _consultation(client, h, patient["id"])
    r = client.post(
        "/api/scribe/transcribe",
        json={"consultation_id": cons["id"], "text_hint": "test", "consent_audio": False},
        headers=h,
    )
    assert r.json()["audio_retained"] is False
