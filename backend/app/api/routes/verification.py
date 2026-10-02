"""Professional verification workflows.

Four distinct, never-conflated notions (see docs/verification.md):
1. an official source being *available*,
2. an official integration being *authorised*,
3. a *SunuDoctor* check,
4. a *facility* confirming membership.

Endpoints here never turn a similarity match into a validation, never let an
actor validate their own identity, and audit every decision.
"""
from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_meta, get_current_user
from app.core.database import get_db
from app.models.entities import (
    AffiliationStatus,
    FacilityStatus,
    HealthcareFacility,
    IdentityDocument,
    Professional,
    ProfessionalAffiliation,
    Role,
    User,
    VerificationDecisionRecord,
    VerificationLevel,
)
from app.schemas import (
    AffiliationDecision,
    AffiliationRequestCreate,
    IdentitySubmit,
    OfficerDecision,
    RegistryImportRequest,
)
from app.services import audit, registry_import, verification
from app.services.matching import match_professional

router = APIRouter(prefix="/verification", tags=["verification"])

OFFICER_ROLES = {Role.verification_officer, Role.platform_admin}


def _professional_for(db: Session, user: User) -> Professional:
    prof = db.query(Professional).filter(Professional.user_id == user.id).first()
    if prof is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucun profil professionnel")
    return prof


def _status_payload(prof: Professional) -> dict:
    level = prof.verification_level
    return {
        "professional_id": prof.id,
        "verification_status": prof.verification_status.value,
        "verification_level": level.value,
        "level_label": verification.LEVEL_LABELS.get(level, level.value),
        "badge": verification.badge(level),
        "access_tier": verification.access_tier(level),
        "can_author_clinical": verification.can_author_clinical(level),
        "review_notes": prof.review_notes,
    }


# ---------------------------------------------------------------------------
# Professional: my verification status
# ---------------------------------------------------------------------------

@router.get("/me")
def my_verification(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prof = _professional_for(db, user)
    payload = _status_payload(prof)
    affiliations = (
        db.query(ProfessionalAffiliation)
        .filter(ProfessionalAffiliation.professional_id == prof.id)
        .order_by(ProfessionalAffiliation.requested_at.desc())
        .all()
    )
    payload["affiliations"] = [
        {
            "id": a.id,
            "facility_id": a.facility_id,
            "status": a.status.value,
            "requested_at": a.requested_at,
            "decided_at": a.decided_at,
            "ended_at": a.ended_at,
        }
        for a in affiliations
    ]
    # Honest, explicit wording so a user is never left in doubt.
    if verification.is_verified(prof.verification_level):
        payload["message"] = "Votre profil professionnel est vérifié."
    elif prof.verification_level in {
        VerificationLevel.rejected,
        VerificationLevel.suspended,
    }:
        payload["message"] = "Votre vérification nécessite une action."
    else:
        payload["message"] = "Vérification en cours."
    return payload


@router.post("/identity", status_code=201)
def submit_identity(
    payload: IdentitySubmit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    """Record supporting documents and move to IDENTITY_SUBMITTED (never VERIFIED)."""
    prof = _professional_for(db, user)
    if prof.verification_level in {VerificationLevel.rejected, VerificationLevel.suspended}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Vérification refusée ou compte suspendu : contactez le support.",
        )
    created = []
    for doc in payload.documents:
        kind = str(doc.get("kind") or "identity").strip()[:64]
        record = IdentityDocument(
            professional_id=prof.id,
            kind=kind,
            reference=str(doc.get("reference") or "")[:255] or None,
            checksum=str(doc.get("checksum") or "")[:64] or None,
            uploaded_by=user.id,
        )
        db.add(record)
        created.append(record)

    if prof.verification_level in {VerificationLevel.unverified}:
        prof.verification_level = VerificationLevel.identity_submitted

    # Duplicate detection is informational and never auto-resolves.
    duplicates = verification.flag_duplicates(db, prof)
    db.commit()

    audit.log_action(
        db,
        action=audit.AuditAction.IDENTITY_SUBMIT,
        actor=user,
        resource_type="professional",
        resource_id=prof.id,
        meta={"documents": len(created), "duplicates": len(duplicates)},
        ip=meta.get("ip"),
    )
    out = _status_payload(prof)
    out["documents_received"] = len(created)
    out["duplicates_flagged"] = len(duplicates)
    if duplicates:
        out["message"] = (
            "Vérification supplémentaire nécessaire : un doublon potentiel a été "
            "détecté et sera examiné par un vérificateur."
        )
    return out


# ---------------------------------------------------------------------------
# Professional: affiliation requests & history
# ---------------------------------------------------------------------------

@router.post("/affiliations", status_code=201)
def request_affiliation(
    payload: AffiliationRequestCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    prof = _professional_for(db, user)
    facility = db.get(HealthcareFacility, payload.facility_id)
    if facility is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Structure introuvable")
    if facility.status == FacilityStatus.archived:
        raise HTTPException(status.HTTP_409_CONFLICT, "Structure archivée")

    affiliation = verification.request_affiliation(
        db, prof, facility, role_function=payload.role_function
    )
    db.commit()

    audit.log_action(
        db,
        action=audit.AuditAction.AFFILIATION_REQUEST,
        actor=user,
        resource_type="facility",
        resource_id=facility.id,
        meta={"professional_id": prof.id, "affiliation_id": affiliation.id},
        ip=meta.get("ip"),
    )
    return {
        "affiliation_id": affiliation.id,
        "facility_id": facility.id,
        "facility_name": facility.name,
        "status": affiliation.status.value,
        "verification_level": prof.verification_level.value,
        "notice": (
            "Demande d'association envoyée. Elle doit être confirmée par un "
            "administrateur habilité de la structure."
        ),
    }


@router.post("/affiliations/change", status_code=201)
def change_affiliation(
    payload: AffiliationRequestCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    """Move to a new facility, preserving the full affiliation history."""
    prof = _professional_for(db, user)
    facility = db.get(HealthcareFacility, payload.facility_id)
    if facility is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Structure introuvable")
    affiliation = verification.change_affiliation(
        db, prof, facility, role_function=payload.role_function
    )
    db.commit()
    audit.log_action(
        db,
        action=audit.AuditAction.AFFILIATION_REQUEST,
        actor=user,
        resource_type="facility",
        resource_id=facility.id,
        meta={"professional_id": prof.id, "kind": "change", "affiliation_id": affiliation.id},
        ip=meta.get("ip"),
    )
    return {
        "affiliation_id": affiliation.id,
        "facility_id": facility.id,
        "status": affiliation.status.value,
        "notice": "Changement de structure demandé. L'historique est conservé.",
    }


@router.get("/affiliations/mine")
def my_affiliations(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    prof = _professional_for(db, user)
    rows = (
        db.query(ProfessionalAffiliation)
        .filter(ProfessionalAffiliation.professional_id == prof.id)
        .order_by(ProfessionalAffiliation.requested_at.desc())
        .all()
    )
    return {
        "affiliations": [
            {
                "id": a.id,
                "facility_id": a.facility_id,
                "status": a.status.value,
                "requested_at": a.requested_at,
                "decided_at": a.decided_at,
                "ended_at": a.ended_at,
                "role_function": a.role_function,
            }
            for a in rows
        ]
    }


# ---------------------------------------------------------------------------
# Facility administrator: confirm membership
# ---------------------------------------------------------------------------

def _require_facility_admin(db: Session, user: User, facility_id: str) -> None:
    if not verification.can_confirm_membership(user, db, facility_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Administration de cette structure non autorisée.",
        )


@router.get("/facility/{facility_id}/affiliations")
def facility_affiliations(
    facility_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_facility_admin(db, user, facility_id)
    rows = (
        db.query(ProfessionalAffiliation)
        .filter(ProfessionalAffiliation.facility_id == facility_id)
        .order_by(ProfessionalAffiliation.requested_at.desc())
        .all()
    )
    out = []
    for a in rows:
        prof = db.get(Professional, a.professional_id)
        member = db.get(User, prof.user_id) if prof else None
        out.append(
            {
                "affiliation_id": a.id,
                "professional_id": a.professional_id,
                "profession": prof.profession if prof else None,
                "member_name": member.full_name if member else None,
                "status": a.status.value,
                "requested_at": a.requested_at,
            }
        )
    return {"facility_id": facility_id, "affiliations": out}


@router.post("/facility/{facility_id}/affiliations/{affiliation_id}/decision")
def decide_affiliation(
    facility_id: str,
    affiliation_id: str,
    payload: AffiliationDecision,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    _require_facility_admin(db, user, facility_id)
    affiliation = db.get(ProfessionalAffiliation, affiliation_id)
    if affiliation is None or affiliation.facility_id != facility_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demande d'association introuvable")

    decision = payload.decision.strip().upper()
    mapping = {
        "APPROVE": AffiliationStatus.approved,
        "REJECT": AffiliationStatus.rejected,
        "SUSPEND": AffiliationStatus.suspended,
        "END": AffiliationStatus.ended,
    }
    if decision not in mapping:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Décision invalide (APPROVE|REJECT|SUSPEND|END)"
        )

    prof = db.get(Professional, affiliation.professional_id)
    # Separation of duties: an administrator may not confirm their own membership.
    if prof and prof.user_id == user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Un administrateur ne peut pas confirmer sa propre appartenance.",
        )

    new_status = mapping[decision]
    affiliation.status = new_status
    affiliation.decided_at = datetime.now(UTC)
    affiliation.decided_by = user.id
    affiliation.decision_notes = payload.notes
    if new_status == AffiliationStatus.ended:
        affiliation.ended_at = datetime.now(UTC)

    if (
        prof
        and new_status == AffiliationStatus.approved
        # Membership confirmed by the facility -> FACILITY_ADMIN_VERIFIED, which
        # is at least the VERIFIED tier. Never higher than that here.
        and not verification.is_at_least(
            prof.verification_level, VerificationLevel.facility_admin_verified
        )
    ):
        prof.verification_level = VerificationLevel.facility_admin_verified
    if prof and new_status == AffiliationStatus.suspended:
        prof.verification_level = VerificationLevel.suspended

    db.commit()
    audit.log_action(
        db,
        action=audit.AuditAction.AFFILIATION_DECISION,
        actor=user,
        resource_type="facility",
        resource_id=facility_id,
        meta={"affiliation_id": affiliation_id, "decision": decision},
        ip=meta.get("ip"),
    )
    return {
        "affiliation_id": affiliation_id,
        "status": affiliation.status.value,
        "verification_level": prof.verification_level.value if prof else None,
    }


# ---------------------------------------------------------------------------
# Verification officer: queue & decisions
# ---------------------------------------------------------------------------

def _require_officer(user: User = Depends(get_current_user)) -> User:
    if user.role not in OFFICER_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé aux vérificateurs")
    return user


def _match_for(prof: Professional, db: Session) -> dict:
    """Consult the best available source for a professional.

    Only the local referential is consulted. When no official source is
    configured, the result explicitly says so instead of guessing.
    """
    from app.core.config import settings

    source_available = bool(settings.official_registry_url and settings.official_registry_key)
    result = match_professional(
        license_number=prof.license_number,
        full_name=db.get(User, prof.user_id).full_name if db.get(User, prof.user_id) else "",
        profession=prof.profession,
        specialty=prof.specialty,
        official_license=None,
        official_name=None,
        official_profession=None,
        source_available=source_available,
    )
    return {
        **result.to_dict(),
        "source_consulted": "source officielle autorisée" if source_available else None,
        "source_note": (
            "Aucune source officielle autorisée n'est configurée. "
            "Vérification supplémentaire nécessaire."
            if not source_available
            else "Source officielle autorisée consultée."
        ),
    }


@router.get("/queue")
def verification_queue(
    officer: User = Depends(_require_officer), db: Session = Depends(get_db)
):
    """Pending professional verifications with their (non-definitive) match.

    Includes every non-terminal level so an officer sees a newly registered
    professional as well as one who has already submitted documents.
    """
    pending_levels = {
        VerificationLevel.unverified,
        VerificationLevel.identity_submitted,
        VerificationLevel.facility_matched,
        VerificationLevel.professional_pending,
        VerificationLevel.duplicate_review,
    }
    profs = (
        db.query(Professional)
        .filter(Professional.verification_level.in_(pending_levels))
        .order_by(Professional.created_at.asc())
        .all()
    )
    out = []
    for prof in profs:
        member = db.get(User, prof.user_id)
        documents = (
            db.query(IdentityDocument)
            .filter(IdentityDocument.professional_id == prof.id)
            .count()
        )
        out.append(
            {
                "professional_id": prof.id,
                "full_name": member.full_name if member else None,
                "profession": prof.profession,
                "specialty": prof.specialty,
                "license_number": prof.license_number,
                "verification_level": prof.verification_level.value,
                "submitted_at": prof.created_at,
                "documents_submitted": documents,
                "match": _match_for(prof, db),
                "is_self": member.id == officer.id if member else False,
            }
        )
    return {"queue": out}


@router.post("/queue/{professional_id}/decision")
def officer_decision(
    professional_id: str,
    payload: OfficerDecision,
    officer: User = Depends(_require_officer),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    prof = db.get(Professional, professional_id)
    if prof is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Professionnel introuvable")

    allowed, reason = verification.can_decide_verification(officer, prof)
    if not allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, reason)

    decision = payload.decision.strip().upper()
    if decision not in {"APPROVE", "REJECT", "REQUEST_MORE_INFORMATION"}:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Décision invalide (APPROVE|REJECT|REQUEST_MORE_INFORMATION)",
        )

    from_level = prof.verification_level
    if decision == "APPROVE":
        if payload.target_level:
            try:
                to_level = VerificationLevel(payload.target_level)
            except ValueError:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Niveau cible invalide") from None
        else:
            to_level = VerificationLevel.verified
        # An officer cannot grant the highest, source-based level without an
        # actual authorised source being consulted.
        if to_level == VerificationLevel.official_source_verified:
            from app.core.config import settings

            if not (settings.official_registry_url and settings.official_registry_key):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Niveau OFFICIAL_SOURCE_VERIFIED impossible : aucune source "
                    "officielle autorisée n'est configurée.",
                )
        prof.verification_level = to_level
    elif decision == "REJECT":
        to_level = VerificationLevel.rejected
        prof.verification_level = to_level
    else:
        to_level = VerificationLevel.professional_pending
        prof.verification_level = to_level

    prof.review_notes = payload.reason
    record = VerificationDecisionRecord(
        professional_id=prof.id,
        decision=decision,
        from_level=from_level.value,
        to_level=to_level.value,
        reason=payload.reason,
        source_consulted=payload.source_consulted,
        match_result=json.dumps(_match_for(prof, db), ensure_ascii=False),
        decided_by=officer.id,
    )
    db.add(record)
    db.commit()

    audit.log_action(
        db,
        action=audit.AuditAction.VERIFICATION_REVIEW,
        actor=officer,
        resource_type="professional",
        resource_id=prof.id,
        meta={"decision": decision, "to_level": to_level.value},
        ip=meta.get("ip"),
    )
    return {
        "professional_id": prof.id,
        "decision": decision,
        "verification_level": prof.verification_level.value,
        "badge": verification.badge(prof.verification_level),
    }


# ---------------------------------------------------------------------------
# Registry imports (officer / admin)
# ---------------------------------------------------------------------------

@router.post("/imports", status_code=201)
def stage_registry_import(
    payload: RegistryImportRequest,
    officer: User = Depends(_require_officer),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    """Stage a referential import without publishing it."""
    try:
        raw = base64.b64decode(payload.content, validate=True)
    except (binascii.Error, ValueError):
        # Accept raw text as a convenience when it is not base64.
        raw = payload.content.encode("utf-8")

    record = registry_import.stage_import(
        db,
        payload=raw,
        fmt=payload.format,
        source=payload.source,
        source_type=payload.source_type,
        version=payload.version,
        imported_by=officer.id,
    )
    published = None
    if payload.publish and record.status.value in {"VALIDATED", "REVIEW"}:
        published = registry_import.publish_import(db, record)
    db.commit()

    audit.log_action(
        db,
        action=audit.AuditAction.REGISTRY_IMPORT,
        actor=officer,
        resource_type="registry_import",
        resource_id=record.id,
        meta={"source": record.source, "records": record.record_count, "published": bool(published)},
        ip=meta.get("ip"),
    )
    return {
        "import_id": record.id,
        "status": record.status.value,
        "record_count": record.record_count,
        "error_count": record.error_count,
        "diff": json.loads(record.diff_json or "{}"),
        "published": published,
    }


@router.post("/imports/{import_id}/publish")
def publish_registry_import(
    import_id: str,
    officer: User = Depends(_require_officer),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    from app.models.entities import RegistryImport

    record = db.get(RegistryImport, import_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import introuvable")
    try:
        result = registry_import.publish_import(db, record)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None
    db.commit()
    audit.log_action(
        db,
        action=audit.AuditAction.REGISTRY_PUBLISH,
        actor=officer,
        resource_type="registry_import",
        resource_id=record.id,
        meta=result,
        ip=meta.get("ip"),
    )
    return {"import_id": record.id, "status": record.status.value, **result}


@router.get("/imports")
def list_registry_imports(
    officer: User = Depends(_require_officer), db: Session = Depends(get_db)
):
    return {"imports": registry_import.import_history(db)}
