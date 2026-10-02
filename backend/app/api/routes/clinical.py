"""Documents, appointments and teleconsultation.

Teleconsultation now has a real, secure WebRTC signalling path: a professional
accepts a request, a private room token is issued, and only the two authorized
participants can exchange offer/answer/ICE envelopes. Media never transits the
server. Video is still reported as "configuration requise" until the operator
provides real TURN servers — the API never claims a live call without them.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_meta, get_current_user
from app.core.database import get_db
from app.core.rbac import can_access_patient
from app.models.entities import (
    Appointment,
    Document,
    Patient,
    Role,
    Teleconsultation,
    User,
)
from app.schemas import DocumentCreate, SignalRequest, TeleconsultationCreate
from app.services import audit

router = APIRouter(tags=["clinical"])

CLINICAL_WRITERS = {
    Role.doctor,
    Role.nurse,
    Role.midwife,
    Role.other_professional,
    Role.community_agent,
    Role.social_worker,
}


def _require_patient_access(db: Session, user: User, patient_id: str) -> None:
    if db.get(Patient, patient_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient introuvable")
    if not can_access_patient(db, user, patient_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès non autorisé")


# ---------------- Documents ----------------
@router.post("/documents", status_code=201)
def create_document(
    payload: DocumentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    if user.role not in CLINICAL_WRITERS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle non autorisé")
    if payload.patient_id:
        _require_patient_access(db, user, payload.patient_id)
    doc = Document(**payload.model_dump(), created_by=user.id, status="draft", version=1)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    if payload.doc_type == "prescription":
        audit.log_action(
            db,
            action=audit.AuditAction.PRESCRIPTION_CREATE,
            actor=user,
            resource_type="document",
            resource_id=doc.id,
            patient_id=payload.patient_id,
            ip=meta.get("ip"),
        )
    return {"id": doc.id, "title": doc.title, "version": doc.version, "status": doc.status}


@router.get("/documents")
def list_documents(
    patient_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Document)
    if patient_id:
        _require_patient_access(db, user, patient_id)
        q = q.filter(Document.patient_id == patient_id)
    else:
        q = q.filter(Document.created_by == user.id)
    docs = q.order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "doc_type": d.doc_type,
            "status": d.status,
            "version": d.version,
            "is_demo": d.is_demo,
            "created_at": d.created_at,
        }
        for d in docs
    ]


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable")
    if doc.patient_id:
        _require_patient_access(db, user, doc.patient_id)
    audit.log_action(
        db,
        action=audit.AuditAction.DOCUMENT_DOWNLOAD,
        actor=user,
        resource_type="document",
        resource_id=doc.id,
        patient_id=doc.patient_id,
        ip=meta.get("ip"),
    )
    return {
        "id": doc.id,
        "title": doc.title,
        "content": doc.content,
        "version": doc.version,
        "status": doc.status,
        "is_demo": doc.is_demo,
        "notice": "Document généré — vérifiez son contenu avant tout usage.",
    }


# ---------------- Appointments ----------------
@router.post("/appointments", status_code=201)
def create_appointment(
    patient_id: str,
    scheduled_at: datetime,
    reason: str | None = None,
    channel: str = "in_person",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_patient_access(db, user, patient_id)
    appt = Appointment(
        patient_id=patient_id,
        professional_id=user.id,
        organization_id=user.organization_id,
        scheduled_at=scheduled_at,
        reason=reason,
        channel=channel,
        status="requested",
        created_by=user.id,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return {"id": appt.id, "status": appt.status, "scheduled_at": appt.scheduled_at}


@router.get("/appointments")
def list_appointments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role in CLINICAL_WRITERS:
        appts = (
            db.query(Appointment)
            .filter(Appointment.professional_id == user.id)
            .order_by(Appointment.scheduled_at)
            .all()
        )
    else:
        appts = (
            db.query(Appointment)
            .filter(Appointment.patient_id == user.id)
            .order_by(Appointment.scheduled_at)
            .all()
        )
    return [
        {
            "id": a.id,
            "patient_id": a.patient_id,
            "scheduled_at": a.scheduled_at,
            "status": a.status,
            "channel": a.channel,
            "reason": a.reason,
        }
        for a in appts
    ]


# ---------------- Teleconsultation ----------------
@router.post("/teleconsultations", status_code=201)
def create_teleconsultation(
    payload: TeleconsultationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    if user.role not in CLINICAL_WRITERS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle non autorisé")
    _require_patient_access(db, user, payload.patient_id)
    tele = Teleconsultation(
        patient_id=payload.patient_id,
        professional_id=user.id,
        status="requested",
        provider="none",  # WebRTC signalling not configured
    )
    db.add(tele)
    db.commit()
    db.refresh(tele)
    return {
        "id": tele.id,
        "status": tele.status,
        "provider": tele.provider,
        "video_status": "configuration_requise",
        "notice": "Vidéo — configuration requise. Aucun service vidéo réel n'est connecté.",
    }


@router.get("/teleconsultations")
def list_teleconsultations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Teleconsultation)
    if user.role in CLINICAL_WRITERS:
        q = q.filter(Teleconsultation.professional_id == user.id)
    else:
        q = q.filter(Teleconsultation.patient_id == user.id)
    return [
        {
            "id": t.id,
            "patient_id": t.patient_id,
            "status": t.status,
            "provider": t.provider,
            "video_status": "configuration_requise" if t.provider == "none" else "pret",
            "report": t.report,
        }
        for t in q.order_by(Teleconsultation.created_at.desc()).all()
    ]


@router.post("/teleconsultations/{tele_id}/report")
def set_report(
    tele_id: str,
    report: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tele = db.get(Teleconsultation, tele_id)
    if tele is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Téléconsultation introuvable")
    if tele.professional_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Non autorisé")
    tele.report = report
    tele.status = "completed"
    tele.ended_at = datetime.now(UTC)
    db.commit()
    return {"id": tele.id, "status": tele.status}


@router.get("/teleconsultations/ice-servers")
def ice_servers():
    """Return ICE server configuration for the WebRTC client.

    STUN is public. TURN requires operator-provided credentials. ``configured``
    is True only when a TURN server is present, because without TURN many mobile
    networks cannot establish a peer connection. The client must show
    "Vidéo — configuration requise" while ``configured`` is False.
    """
    from app.core.config import settings

    return {
        "configured": settings.turn_configured,
        "ice_servers": settings.ice_servers,
        "turn_configured": settings.turn_configured,
        "notice": (
            "Serveurs ICE fournis. La visioconsultation peut être négociée."
            if settings.turn_configured
            else "Vidéo — configuration requise. Fournissez des serveurs TURN réels "
            "pour activer la visioconsultation."
        ),
    }


@router.post("/teleconsultations/{tele_id}/accept")
def accept_teleconsultation(
    tele_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    """Professional accepts a teleconsultation request and opens a room.

    A room is created only for an authorized participant. The room reference is
    a random, unguessable token — never a public room name.
    """
    import secrets

    tele = db.get(Teleconsultation, tele_id)
    if tele is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Téléconsultation introuvable")
    if tele.professional_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Non autorisé")
    from app.core.config import settings

    tele.status = "accepted"
    tele.provider = "webrtc" if settings.turn_configured else "none"
    tele.room_ref = secrets.token_urlsafe(24)
    db.commit()
    audit.log_action(
        db,
        action="teleconsultation_accept",
        actor=user,
        resource_type="teleconsultation",
        resource_id=tele.id,
        patient_id=tele.patient_id,
        ip=meta.get("ip"),
    )
    return {
        "id": tele.id,
        "status": tele.status,
        "provider": tele.provider,
        "room_ref": tele.room_ref,
        "video_status": "pret" if settings.turn_configured else "configuration_requise",
    }


@router.post("/teleconsultations/{tele_id}/signal")
def post_signal(
    tele_id: str,
    payload: SignalRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Store a WebRTC signalling envelope (offer/answer/ICE candidate/bye).

    Only the two participants of the teleconsultation may post or read signals
    for its room. Messages expire quickly. Media never transits the server.
    """
    from datetime import timedelta

    from app.models.entities import SignalingMessage

    kind = payload.kind
    if kind not in {"offer", "answer", "candidate", "bye"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type de signal invalide")
    tele = db.get(Teleconsultation, tele_id)
    if tele is None or not tele.room_ref:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session introuvable")
    if user.id not in {tele.professional_id, _patient_owner_id(db, tele.patient_id)}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Participant non autorisé")
    now = datetime.now(UTC)
    msg = SignalingMessage(
        room_ref=tele.room_ref,
        sender_id=user.id,
        kind=kind,
        payload_json=json.dumps(payload.payload, ensure_ascii=False),
        created_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    db.add(msg)
    db.commit()
    return {"id": msg.id, "kind": kind}


@router.get("/teleconsultations/{tele_id}/signal")
def get_signals(
    tele_id: str,
    since_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Poll signalling envelopes for a room, excluding the caller's own."""
    from app.models.entities import SignalingMessage

    tele = db.get(Teleconsultation, tele_id)
    if tele is None or not tele.room_ref:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session introuvable")
    if user.id not in {tele.professional_id, _patient_owner_id(db, tele.patient_id)}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Participant non autorisé")
    now = datetime.now(UTC)
    q = (
        db.query(SignalingMessage)
        .filter(SignalingMessage.room_ref == tele.room_ref)
        .filter(SignalingMessage.sender_id != user.id)
        .filter(SignalingMessage.expires_at > now)
    )
    msgs = q.order_by(SignalingMessage.created_at).all()
    return [
        {
            "id": m.id,
            "kind": m.kind,
            "payload": json.loads(m.payload_json),
            "sender_id": m.sender_id,
            "created_at": m.created_at,
        }
        for m in msgs
    ]


def _patient_owner_id(db: Session, patient_id: str) -> str | None:
    """The user id that owns a patient record (via the patient's own grant)."""
    from app.models.entities import CareTeamAccess, Role
    from app.models.entities import User as UserModel

    row = (
        db.query(CareTeamAccess)
        .join(UserModel, UserModel.id == CareTeamAccess.user_id)
        .filter(CareTeamAccess.patient_id == patient_id, UserModel.role == Role.patient)
        .first()
    )
    return row.user_id if row else None
