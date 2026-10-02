"""Professional verification: levels, badges, duplicate detection, access tiers.

Design rules enforced here:

* A new account is always ``UNVERIFIED``.
* Nothing raises a level automatically. Facility matching only records
  ``FACILITY_MATCHED`` (a factual, reversible observation), never ``VERIFIED``.
* A human decision (verification officer, facility administrator) or an explicit
  official-source confirmation is required for the higher levels.
* Badge wording never claims ministerial validation.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.entities import (
    AffiliationStatus,
    FacilityStatus,
    Professional,
    ProfessionalAffiliation,
    ProfessionalDuplicateFlag,
    Role,
    User,
    VerificationLevel,
)
from app.services.matching import similarity

# Ordered ladder used for comparisons. Terminal/negative states are excluded.
_LADDER = [
    VerificationLevel.unverified,
    VerificationLevel.identity_submitted,
    VerificationLevel.facility_matched,
    VerificationLevel.professional_pending,
    VerificationLevel.verified,
    VerificationLevel.facility_admin_verified,
    VerificationLevel.official_source_verified,
]

_NEGATIVE = {
    VerificationLevel.rejected,
    VerificationLevel.suspended,
    VerificationLevel.duplicate_review,
}

LEVEL_LABELS = {
    VerificationLevel.unverified: "Non vérifié",
    VerificationLevel.identity_submitted: "Identité transmise",
    VerificationLevel.facility_matched: "Structure reconnue",
    VerificationLevel.professional_pending: "Professionnel en attente",
    VerificationLevel.verified: "Professionnel vérifié",
    VerificationLevel.facility_admin_verified: "Appartenance confirmée",
    VerificationLevel.official_source_verified: "Vérifié via source institutionnelle autorisée",
    VerificationLevel.rejected: "Vérification refusée",
    VerificationLevel.suspended: "Compte suspendu",
    VerificationLevel.duplicate_review: "Revue de doublon",
}


def level_rank(level: VerificationLevel) -> int:
    if level in _NEGATIVE:
        return -1
    return _LADDER.index(level)


def is_at_least(level: VerificationLevel, minimum: VerificationLevel) -> bool:
    if level in _NEGATIVE:
        return False
    return level_rank(level) >= level_rank(minimum)


def is_verified(level: VerificationLevel) -> bool:
    return is_at_least(level, VerificationLevel.verified)


def badge(level: VerificationLevel) -> dict:
    """Return an honest badge.

    ``verified_by`` distinguishes SunuDoctor's own check, a facility's
    confirmation, and an authorised institutional source. It never says
    "Ministère de la Santé" unless that confirmation was actually obtained.
    """
    if level == VerificationLevel.official_source_verified:
        return {
            "level": level.value,
            "label": "Vérifié via source institutionnelle autorisée",
            "verified_by": "source institutionnelle autorisée",
            "icon": "verified",
            "tone": "success",
        }
    if level == VerificationLevel.facility_admin_verified:
        return {
            "level": level.value,
            "label": "Appartenance à la structure confirmée",
            "verified_by": "structure de santé",
            "icon": "verified",
            "tone": "success",
        }
    if level == VerificationLevel.verified:
        return {
            "level": level.value,
            "label": "Vérifié par SunuDoctor",
            "verified_by": "SunuDoctor",
            "icon": "verified",
            "tone": "success",
        }
    if level == VerificationLevel.rejected:
        return {
            "level": level.value,
            "label": "Vérification refusée",
            "verified_by": None,
            "icon": "rejected",
            "tone": "danger",
        }
    if level == VerificationLevel.suspended:
        return {
            "level": level.value,
            "label": "Compte suspendu",
            "verified_by": None,
            "icon": "suspended",
            "tone": "danger",
        }
    if level == VerificationLevel.duplicate_review:
        return {
            "level": level.value,
            "label": "Revue de doublon en cours",
            "verified_by": None,
            "icon": "warning",
            "tone": "warning",
        }
    return {
        "level": level.value,
        "label": "Vérification en cours",
        "verified_by": None,
        "icon": "pending",
        "tone": "pending",
    }


# Access tiers: an unverified account never gets full professional capability.
ACCESS_LIMITED = "LIMITED"
ACCESS_PROFESSIONAL = "PROFESSIONAL"
ACCESS_STRUCTURE = "STRUCTURE"


def access_tier(level: VerificationLevel) -> str:
    if is_at_least(level, VerificationLevel.facility_admin_verified):
        return ACCESS_STRUCTURE
    if is_at_least(level, VerificationLevel.verified):
        return ACCESS_PROFESSIONAL
    return ACCESS_LIMITED


def can_author_clinical(level: VerificationLevel) -> bool:
    """Only a verified professional may author clinical content."""
    return is_at_least(level, VerificationLevel.verified)


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def _current_facility_id(db: Session, professional: Professional) -> str | None:
    """The professional's approved (or pending) facility, if any."""
    affiliation = (
        db.query(ProfessionalAffiliation)
        .filter(
            ProfessionalAffiliation.professional_id == professional.id,
            ProfessionalAffiliation.status.in_(
                [AffiliationStatus.requested, AffiliationStatus.approved]
            ),
        )
        .order_by(ProfessionalAffiliation.requested_at.desc())
        .first()
    )
    return affiliation.facility_id if affiliation else None


def find_duplicates(db: Session, professional: Professional) -> list[tuple[str, str]]:
    """Return (matched_professional_id, reason) pairs for suspected duplicates.

    Detection is informational: a suspected duplicate is never deleted or merged
    automatically; it is routed to human review. A weak signal (name similarity
    alone) is deliberately NOT enough: the specification requires a combination
    of name, profession and structure.
    """
    user = db.get(User, professional.user_id)
    if user is None:
        return []

    found: list[tuple[str, str]] = []
    my_facility = _current_facility_id(db, professional)
    others = (
        db.query(Professional)
        .filter(Professional.id != professional.id)
        .all()
    )
    for other in others:
        other_user = db.get(User, other.user_id)
        if other_user is None:
            continue

        if (
            professional.license_number
            and other.license_number
            and professional.license_number.strip().lower()
            == other.license_number.strip().lower()
        ):
            found.append((other.id, "same_license_number"))
            continue

        if other_user.email and user.email and other_user.email.lower() == user.email.lower():
            found.append((other.id, "same_email"))
            continue

        if user.phone and other_user.phone and user.phone == other_user.phone:
            found.append((other.id, "same_phone"))
            continue

        # Name + profession + same structure. Without a shared structure this is
        # not a duplicate signal, only a common name.
        if (
            my_facility
            and my_facility == _current_facility_id(db, other)
            and similarity(user.full_name, other_user.full_name) >= 0.92
            and (professional.profession or "") == (other.profession or "")
        ):
            found.append((other.id, "same_name_profession_facility"))
    return found


def flag_duplicates(db: Session, professional: Professional) -> list[ProfessionalDuplicateFlag]:
    """Record duplicate flags and move the professional to DUPLICATE_REVIEW."""
    created: list[ProfessionalDuplicateFlag] = []
    for matched_id, reason in find_duplicates(db, professional):
        exists = (
            db.query(ProfessionalDuplicateFlag)
            .filter(
                ProfessionalDuplicateFlag.professional_id == professional.id,
                ProfessionalDuplicateFlag.matched_professional_id == matched_id,
                ProfessionalDuplicateFlag.resolved.is_(False),
            )
            .first()
        )
        if exists:
            continue
        flag = ProfessionalDuplicateFlag(
            professional_id=professional.id,
            matched_professional_id=matched_id,
            reason=reason,
            detail="Détection automatique : revue humaine requise, aucune fusion automatique.",
        )
        db.add(flag)
        created.append(flag)

    if created:
        professional.verification_level = VerificationLevel.duplicate_review
        professional.review_notes = (
            "Doublon potentiel détecté. Vérification supplémentaire nécessaire."
        )
    return created


# ---------------------------------------------------------------------------
# Affiliation history
# ---------------------------------------------------------------------------

def request_affiliation(
    db: Session,
    professional: Professional,
    facility,
    *,
    role_function: str | None = None,
) -> ProfessionalAffiliation:
    """Create a REQUESTED affiliation. Never auto-approved."""
    existing = (
        db.query(ProfessionalAffiliation)
        .filter(
            ProfessionalAffiliation.professional_id == professional.id,
            ProfessionalAffiliation.facility_id == facility.id,
            ProfessionalAffiliation.status.in_(
                [AffiliationStatus.requested, AffiliationStatus.approved]
            ),
        )
        .first()
    )
    if existing:
        return existing

    affiliation = ProfessionalAffiliation(
        professional_id=professional.id,
        facility_id=facility.id,
        role_function=role_function,
        status=AffiliationStatus.requested,
    )
    db.add(affiliation)
    db.flush()

    # A recognised facility (not just a name typed by the user) moves the level
    # to FACILITY_MATCHED at most. It never reaches VERIFIED here.
    if facility.status in {
        FacilityStatus.official_verified,
        FacilityStatus.partner_verified,
    } and not is_at_least(professional.verification_level, VerificationLevel.facility_matched):
        professional.verification_level = VerificationLevel.facility_matched
    return affiliation


def change_affiliation(
    db: Session,
    professional: Professional,
    new_facility,
    *,
    role_function: str | None = None,
) -> ProfessionalAffiliation:
    """Move a professional to a new facility, preserving history.

    Every currently-approved affiliation is ended (never deleted) before the new
    one is requested, so the trajectory stays auditable.
    """
    now = datetime.now(UTC)
    open_affiliations = (
        db.query(ProfessionalAffiliation)
        .filter(
            ProfessionalAffiliation.professional_id == professional.id,
            ProfessionalAffiliation.status == AffiliationStatus.approved,
        )
        .all()
    )
    for old in open_affiliations:
        old.status = AffiliationStatus.ended
        old.ended_at = now

    return request_affiliation(db, professional, new_facility, role_function=role_function)


# ---------------------------------------------------------------------------
# Self-verification prevention
# ---------------------------------------------------------------------------

def can_decide_verification(actor: User, professional: Professional) -> tuple[bool, str]:
    """Prevent an actor from validating their own identity.

    Returns (allowed, reason). A self-decision is always refused and must go
    through an independent officer.
    """
    if actor.id == professional.user_id:
        return (
            False,
            "Un compte ne peut pas valider sa propre identité. "
            "La demande doit être traitée par un vérificateur indépendant.",
        )
    return True, ""


def can_confirm_membership(actor: User, db: Session, facility_id: str) -> bool:
    """A facility membership can only be confirmed by a granted facility admin.

    Holding an administrative role is not sufficient on its own: the grant must
    be scoped to this exact facility and not revoked.
    """
    from app.models.entities import FacilityAdminGrant

    if actor.role not in {Role.org_admin, Role.verification_officer, Role.platform_admin}:
        return False
    grant = (
        db.query(FacilityAdminGrant)
        .filter(
            FacilityAdminGrant.user_id == actor.id,
            FacilityAdminGrant.facility_id == facility_id,
            FacilityAdminGrant.revoked_at.is_(None),
        )
        .first()
    )
    return grant is not None
