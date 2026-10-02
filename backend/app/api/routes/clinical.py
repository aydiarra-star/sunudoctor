"""Documents, appointments and teleconsultation.

Video is prepared with a WebRTC-ready architecture but is NOT operational until
a real signalling service is configured. The API reports ``provider="none"`` and
the UI must display "Vidéo — configuration requise". It never claims a live call.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_meta, get_current_user
from app.core.config import settings
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
from app.schemas import DocumentCreate, TeleconsultationCreate
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
    tele.ended_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": tele.id, "status": tele.status}


@router.get("/teleconsultations/ice-servers")
def ice_servers():
    """Return ICE server configuration for a future WebRTC client.

    Without real TURN/STUN credentials the list is empty and ``configured`` is
    False, so the client knows video cannot work yet.
    """
    return {
        "configured": False,
        "ice_servers": [],
        "notice": "Vidéo — configuration requise. Fournissez des serveurs ICE (STUN/TURN) "
        "réels pour activer la visioconsultation.",
    }
