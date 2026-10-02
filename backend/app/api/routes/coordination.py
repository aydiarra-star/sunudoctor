"""Messaging, care coordination, consents and break-glass access."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_meta, get_current_user
from app.core.database import get_db
from app.core.rbac import can_access_patient
from app.models.entities import (
    BreakGlassEvent,
    Consent,
    Message,
    Patient,
    Referral,
    Role,
    User,
)
from app.schemas import BreakGlassRequest, ConsentCreate, MessageCreate, ReferralCreate
from app.services import audit

router = APIRouter(tags=["coordination"])

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


# ---------------- Messaging ----------------
@router.post("/messages", status_code=201)
def send_message(
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.patient_id:
        _require_patient_access(db, user, payload.patient_id)
    recipient = db.get(User, payload.recipient_id)
    if recipient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Destinataire introuvable")
    thread = "-".join(sorted([user.id, payload.recipient_id])) + (
        f"-{payload.patient_id}" if payload.patient_id else ""
    )
    msg = Message(
        thread_id=thread,
        sender_id=user.id,
        recipient_id=payload.recipient_id,
        patient_id=payload.patient_id,
        body=payload.body,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "thread_id": msg.thread_id, "created_at": msg.created_at}


@router.get("/messages")
def list_messages(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    msgs = (
        db.query(Message)
        .filter((Message.sender_id == user.id) | (Message.recipient_id == user.id))
        .order_by(Message.created_at.desc())
        .all()
    )
    return [
        {
            "id": m.id,
            "thread_id": m.thread_id,
            "sender_id": m.sender_id,
            "recipient_id": m.recipient_id,
            "patient_id": m.patient_id,
            "body": m.body,
            "read": m.read_at is not None,
            "created_at": m.created_at,
        }
        for m in msgs
    ]


# ---------------- Coordination / referrals ----------------
@router.post("/referrals", status_code=201)
def create_referral(
    payload: ReferralCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    if user.role not in CLINICAL_WRITERS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle non autorisé")
    _require_patient_access(db, user, payload.patient_id)
    ref = Referral(
        patient_id=payload.patient_id,
        from_user_id=user.id,
        to_user_id=payload.to_user_id,
        from_org_id=user.organization_id,
        to_org_id=payload.to_org_id,
        reason=payload.reason,
        priority=payload.priority,
        status="created",
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return {"id": ref.id, "status": ref.status, "priority": ref.priority}


@router.get("/referrals")
def list_referrals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    refs = (
        db.query(Referral)
        .filter((Referral.from_user_id == user.id) | (Referral.to_user_id == user.id))
        .order_by(Referral.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "patient_id": r.patient_id,
            "reason": r.reason,
            "priority": r.priority,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in refs
    ]


@router.post("/referrals/{referral_id}/advance")
def advance_referral(
    referral_id: str,
    new_status: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trace each step of the care pathway: created -> accepted -> seen -> closed."""
    ref = db.get(Referral, referral_id)
    if ref is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Orientation introuvable")
    if user.id not in {ref.from_user_id, ref.to_user_id} and user.role != Role.platform_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Non autorisé")
    if new_status not in {"created", "accepted", "seen", "closed", "declined"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Statut invalide")
    ref.status = new_status
    db.commit()
    return {"id": ref.id, "status": ref.status}


# ---------------- Consents ----------------
@router.post("/consents", status_code=201)
def set_consent(
    payload: ConsentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    valid_scopes = {"access", "share", "teleconsultation", "audio", "ai", "research"}
    if payload.scope not in valid_scopes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Portée de consentement invalide")
    _require_patient_access(db, user, payload.patient_id)
    consent = Consent(
        patient_id=payload.patient_id,
        grantee_id=payload.grantee_id,
        scope=payload.scope,
        granted=payload.granted,
        granted_at=datetime.now(timezone.utc) if payload.granted else None,
        revoked_at=None if payload.granted else datetime.now(timezone.utc),
        document_ref=payload.document_ref,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    audit.log_action(
        db,
        action="consent_change",
        actor=user,
        resource_type="consent",
        resource_id=consent.id,
        patient_id=payload.patient_id,
        meta={"scope": payload.scope, "granted": payload.granted},
        ip=meta.get("ip"),
    )
    return {"id": consent.id, "scope": consent.scope, "granted": consent.granted}


@router.get("/consents")
def list_consents(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_patient_access(db, user, patient_id)
    consents = db.query(Consent).filter(Consent.patient_id == patient_id).all()
    return [
        {
            "id": c.id,
            "scope": c.scope,
            "granted": c.granted,
            "granted_at": c.granted_at,
            "revoked_at": c.revoked_at,
        }
        for c in consents
    ]


# ---------------- Break glass ----------------
@router.post("/break-glass")
def break_glass(
    payload: BreakGlassRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    """Exceptional access. Reason, duration and audit are mandatory."""
    if user.role not in CLINICAL_WRITERS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle non autorisé")
    if db.get(Patient, payload.patient_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient introuvable")
    if not payload.reason or len(payload.reason.strip()) < 10:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Une raison détaillée est obligatoire pour un accès exceptionnel"
        )
    if payload.duration_minutes <= 0 or payload.duration_minutes > 24 * 60:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Durée invalide (max 24h)")

    entry = audit.log_action(
        db,
        action=audit.AuditAction.BREAK_GLASS,
        actor=user,
        resource_type="patient",
        resource_id=payload.patient_id,
        patient_id=payload.patient_id,
        meta={"reason": payload.reason, "duration_minutes": payload.duration_minutes},
        ip=meta.get("ip"),
        commit=False,
    )
    db.flush()
    now = datetime.now(timezone.utc)
    event = BreakGlassEvent(
        actor_id=user.id,
        patient_id=payload.patient_id,
        reason=payload.reason,
        duration_minutes=payload.duration_minutes,
        started_at=now,
        expires_at=now + timedelta(minutes=payload.duration_minutes),
        audit_log_id=entry.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {
        "id": event.id,
        "expires_at": event.expires_at,
        "notice": "Accès exceptionnel enregistré et audité. Il expirera automatiquement.",
    }
