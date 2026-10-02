"""Patient records with resource-scoped RBAC.

Access to a patient record is granted explicitly through CareTeamAccess. There
is no "admin sees everything" shortcut: platform/org admins are administratively
scoped and their clinical reads are audited and require an explicit grant.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_meta, get_current_user
from app.core.database import get_db
from app.core.rbac import can_access_patient
from app.models.entities import (
    Allergy,
    CareTeamAccess,
    Medication,
    Observation,
    Patient,
    Role,
    User,
)
from app.schemas import PatientCreate, PatientOut
from app.services import audit

router = APIRouter(prefix="/patients", tags=["patients"])

CLINICAL_WRITERS = {
    Role.doctor,
    Role.nurse,
    Role.midwife,
    Role.other_professional,
    Role.community_agent,
    Role.social_worker,
}


def _ensure_access(db: Session, user: User, patient_id: str) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient introuvable")
    if not can_access_patient(db, user, patient_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès au dossier non autorisé")
    return patient


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(
    payload: PatientCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    if user.role not in CLINICAL_WRITERS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle non autorisé à créer un patient")
    patient = Patient(
        **payload.model_dump(),
        created_by=user.id,
        organization_id=user.organization_id,
    )
    db.add(patient)
    db.flush()
    # The creator immediately receives a full care-team grant.
    db.add(
        CareTeamAccess(
            patient_id=patient.id,
            user_id=user.id,
            level="full",
            granted_by=user.id,
            reason="Créateur du dossier",
        )
    )
    db.commit()
    db.refresh(patient)
    audit.log_action(
        db,
        action=audit.AuditAction.PATIENT_CREATE,
        actor=user,
        resource_type="patient",
        resource_id=patient.id,
        patient_id=patient.id,
        ip=meta.get("ip"),
        user_agent=meta.get("user_agent"),
    )
    return patient


@router.get("", response_model=list[PatientOut])
def list_patients(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List only patients the user has an explicit grant for."""
    grants = db.query(CareTeamAccess).filter(CareTeamAccess.user_id == user.id).all()
    ids = [g.patient_id for g in grants]
    if not ids:
        return []
    return db.query(Patient).filter(Patient.id.in_(ids)).order_by(Patient.last_name).all()


@router.get("/{patient_id}")
def get_patient(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    patient = _ensure_access(db, user, patient_id)
    # Every clinical read is audited.
    audit.log_action(
        db,
        action=audit.AuditAction.PATIENT_VIEW,
        actor=user,
        resource_type="patient",
        resource_id=patient_id,
        patient_id=patient_id,
        ip=meta.get("ip"),
        user_agent=meta.get("user_agent"),
    )
    return {
        "patient": PatientOut.model_validate(patient),
        "allergies": [
            {"id": a.id, "substance": a.substance, "reaction": a.reaction, "uncertain": a.is_uncertain}
            for a in db.query(Allergy).filter(Allergy.patient_id == patient_id).all()
        ],
        "medications": [
            {
                "id": m.id,
                "name": m.name,
                "dose": m.dose,
                "uncertain": m.is_uncertain,
            }
            for m in db.query(Medication).filter(Medication.patient_id == patient_id).all()
        ],
        "observations": [
            {
                "id": o.id,
                "label": o.label,
                "value": o.value,
                "unit": o.unit,
                "uncertain": o.is_uncertain,
                "recorded_at": o.recorded_at,
            }
            for o in db.query(Observation)
            .filter(Observation.patient_id == patient_id)
            .order_by(Observation.recorded_at.desc())
            .all()
        ],
    }


@router.post("/{patient_id}/access")
def grant_access(
    patient_id: str,
    grantee_id: str,
    level: str = "view",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    _ensure_access(db, user, patient_id)
    if user.role not in CLINICAL_WRITERS and user.role != Role.patient:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permission refusée")
    if level not in {"view", "edit", "full"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Niveau d'accès invalide")
    existing = (
        db.query(CareTeamAccess)
        .filter(CareTeamAccess.patient_id == patient_id, CareTeamAccess.user_id == grantee_id)
        .first()
    )
    if existing:
        existing.level = level
    else:
        db.add(
            CareTeamAccess(
                patient_id=patient_id, user_id=grantee_id, level=level, granted_by=user.id
            )
        )
    db.commit()
    audit.log_action(
        db,
        action=audit.AuditAction.PERMISSION_CHANGE,
        actor=user,
        resource_type="patient",
        resource_id=patient_id,
        patient_id=patient_id,
        meta={"grantee_id": grantee_id, "level": level},
        ip=meta.get("ip"),
    )
    return {"detail": "Accès mis à jour"}
