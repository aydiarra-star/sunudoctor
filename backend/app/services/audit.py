"""Audit logging service.

Every sensitive action (login, record access, modification, export, download,
share, prescription, validation, permission change, break-glass) is written to
``audit_logs`` with the actor, target and timestamp.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.entities import AuditLog, User


def log_action(
    db: Session,
    *,
    action: str,
    actor: User | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    patient_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    meta: dict | None = None,
    commit: bool = True,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        actor_role=actor.role.value if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        patient_id=patient_id,
        ip=ip,
        user_agent=user_agent,
        meta_json=json.dumps(meta or {}, ensure_ascii=False),
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    return entry


# Canonical action names used across the app.
class AuditAction:
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PATIENT_VIEW = "patient_view"
    PATIENT_CREATE = "patient_create"
    PATIENT_UPDATE = "patient_update"
    CONSULTATION_CREATE = "consultation_create"
    CONSULTATION_VALIDATE = "consultation_validate"
    NOTE_MODIFY = "note_modify"
    DOCUMENT_EXPORT = "document_export"
    DOCUMENT_DOWNLOAD = "document_download"
    DOCUMENT_SHARE = "document_share"
    PRESCRIPTION_CREATE = "prescription_create"
    PERMISSION_CHANGE = "permission_change"
    BREAK_GLASS = "break_glass"
    AI_TRANSCRIBE = "ai_transcribe"
    AI_STRUCTURE = "ai_structure"
    PAYMENT_CREATE = "payment_create"
    VERIFICATION_REVIEW = "verification_review"
    EXPORT = "export"
