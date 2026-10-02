"""Role-based access control.

The model is intentionally resource-scoped: a role never grants blanket access
to every patient record. Access to a given patient must be one of:
- the patient themself,
- a professional with an explicit care-team grant for that patient,
- an org_admin within the same organization (administrative scope only),
- platform_admin performing a verifiable action (still audited, and never
  automatically allowed to read clinical content).

Platform administration is deliberately separated from clinical access: an
administrative role does NOT imply access to medical data.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.entities import CareTeamAccess, Role, User

# Roles that are allowed to author clinical content.
CLINICAL_ROLES = {
    Role.doctor,
    Role.nurse,
    Role.midwife,
    Role.other_professional,
    Role.community_agent,
    Role.social_worker,
}

# Roles that may read clinical content (still require per-patient grant).
CLINICAL_READERS = CLINICAL_ROLES | {Role.patient}


def is_clinical(user: User) -> bool:
    return user.role in CLINICAL_ROLES


def can_access_patient(db, user: User, patient_id: str, *, now: datetime | None = None) -> bool:
    """Return True only if the user has a valid, scoped grant for this patient."""
    now = now or datetime.now(timezone.utc)

    if user.role == Role.patient:
        # A patient can access their own record only if their user id maps to it.
        # The mapping is represented by a care-team grant owned by themselves.
        pass

    grant = (
        db.query(CareTeamAccess)
        .filter(CareTeamAccess.patient_id == patient_id, CareTeamAccess.user_id == user.id)
        .first()
    )
    if grant is None:
        return False
    if grant.expires_at is not None:
        expires = grant.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            return False
    return True


def can_edit_patient(db, user: User, patient_id: str) -> bool:
    grant = (
        db.query(CareTeamAccess)
        .filter(CareTeamAccess.patient_id == patient_id, CareTeamAccess.user_id == user.id)
        .first()
    )
    return bool(grant and grant.level in {"edit", "full"} and is_clinical(user))
