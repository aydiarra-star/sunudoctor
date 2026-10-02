"""Platform administration.

Administration is deliberately separated from clinical access. An administrator
can manage users, organizations, verifications, subscriptions and audit logs,
but cannot read clinical content without an explicit, audited grant.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_meta, get_current_user
from app.core.database import get_db
from app.models.entities import (
    AuditLog,
    Organization,
    Professional,
    Role,
    Subscription,
    User,
    VerificationRequest,
    VerificationStatus,
)
from app.schemas import UserOut, VerificationDecision
from app.services import audit

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.platform_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé aux administrateurs")
    return user


@router.get("/users")
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "is_active": u.is_active,
            "organization_id": u.organization_id,
        }
        for u in users
    ]


@router.post("/users/{user_id}/status")
def set_user_status(
    user_id: str,
    is_active: bool,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilisateur introuvable")
    user.is_active = is_active
    db.commit()
    audit.log_action(
        db,
        action=audit.AuditAction.PERMISSION_CHANGE,
        actor=admin,
        resource_type="user",
        resource_id=user_id,
        meta={"is_active": is_active},
        ip=meta.get("ip"),
    )
    return {"id": user_id, "is_active": is_active}


@router.get("/organizations")
def list_organizations(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    orgs = db.query(Organization).order_by(Organization.name).all()
    return [
        {
            "id": o.id,
            "name": o.name,
            "type": o.type,
            "region": o.region,
            "city": o.city,
            "is_demo": o.is_demo,
        }
        for o in orgs
    ]


@router.get("/verifications")
def list_verifications(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Verification queue. Status is NEVER set to verified automatically."""
    reqs = db.query(VerificationRequest).order_by(VerificationRequest.submitted_at).all()
    out = []
    for r in reqs:
        prof = db.get(Professional, r.professional_id)
        out.append(
            {
                "id": r.id,
                "professional_id": r.professional_id,
                "profession": prof.profession if prof else None,
                "license_number": prof.license_number if prof else None,
                "status": r.status.value,
                "submitted_at": r.submitted_at,
                "documents": json.loads(r.documents_json or "[]"),
            }
        )
    return out


@router.post("/verifications/{request_id}/decision")
def decide_verification(
    request_id: str,
    payload: VerificationDecision,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    req = db.get(VerificationRequest, request_id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demande introuvable")
    try:
        new_status = VerificationStatus(payload.status)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Statut invalide")

    req.status = new_status
    req.notes = payload.notes
    req.reviewed_by = admin.id
    req.reviewed_at = datetime.now(timezone.utc)
    prof = db.get(Professional, req.professional_id)
    if prof:
        prof.verification_status = new_status
        prof.review_notes = payload.notes
    db.commit()

    audit.log_action(
        db,
        action=audit.AuditAction.VERIFICATION_REVIEW,
        actor=admin,
        resource_type="professional",
        resource_id=req.professional_id,
        meta={"status": new_status.value},
        ip=meta.get("ip"),
    )
    return {"id": request_id, "status": new_status.value}


@router.get("/subscriptions")
def list_subscriptions(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    subs = db.query(Subscription).order_by(Subscription.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "owner_user_id": s.owner_user_id,
            "organization_id": s.organization_id,
            "plan_code": s.plan_code,
            "price_fcfa": s.price_fcfa,
            "status": s.status,
        }
        for s in subs
    ]


@router.get("/audit")
def list_audit(
    limit: int = 100,
    action: str | None = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    logs = q.order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).all()
    return [
        {
            "id": l.id,
            "actor_id": l.actor_id,
            "actor_role": l.actor_role,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "patient_id": l.patient_id,
            "created_at": l.created_at,
            "meta": json.loads(l.meta_json or "{}"),
        }
        for l in logs
    ]


@router.get("/security/summary")
def security_summary(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Aggregate view for the security dashboard. No clinical content exposed."""
    total = db.query(AuditLog).count()
    break_glass = db.query(AuditLog).filter(AuditLog.action == audit.AuditAction.BREAK_GLASS).count()
    failed = db.query(AuditLog).filter(AuditLog.action == "login_failed").count()
    return {
        "audit_entries": total,
        "break_glass_events": break_glass,
        "failed_logins": failed,
        "separation_of_duties": True,
        "notice": "L'administration technique n'a pas d'accès automatique aux données médicales.",
    }


@router.get("/config")
def platform_config(admin: User = Depends(require_admin)):
    """Non-secret platform configuration. Secrets are never returned."""
    from app.core.config import settings

    return {
        "environment": settings.environment,
        "ai_mode": settings.ai_mode,
        "payment_mode": settings.payment_mode,
        "trial_days": settings.trial_days,
        "secrets_exposed": False,
    }
