"""Authentication: register, login, refresh, logout, MFA stub, profile."""
from __future__ import annotations

import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.api.deps import get_client_meta, get_current_user
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.entities import (
    FacilityStatus,
    HealthcareFacility,
    Organization,
    Professional,
    RegistrySourceType,
    Role,
    User,
    VerificationLevel,
    VerificationRequest,
    VerificationStatus,
)
from app.schemas import (
    LoginRequest,
    MeOut,
    ProfessionalOut,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services import audit, verification

router = APIRouter(prefix="/auth", tags=["auth"])

SELF_REGISTER_ROLES = {
    "patient": Role.patient,
    "doctor": Role.doctor,
    "nurse": Role.nurse,
    "midwife": Role.midwife,
    "other_professional": Role.other_professional,
    "community_agent": Role.community_agent,
    "social_worker": Role.social_worker,
    "org_admin": Role.org_admin,
}

PROFESSIONAL_ROLES = {
    Role.doctor,
    Role.nurse,
    Role.midwife,
    Role.other_professional,
    Role.community_agent,
    Role.social_worker,
}


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    if payload.role not in SELF_REGISTER_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rôle non autorisé à l'inscription")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà pour cet e-mail")

    role = SELF_REGISTER_ROLES[payload.role]

    org = None
    if payload.organization_name:
        org = Organization(name=payload.organization_name, type="cabinet")
        db.add(org)
        db.flush()

    # Professional registration must reference a facility from the referential.
    # A free-text name only creates an UNVERIFIED, PENDING_VERIFICATION request;
    # it never becomes an official facility automatically.
    facility = None
    if role in PROFESSIONAL_ROLES:
        if payload.facility_id:
            facility = db.get(HealthcareFacility, payload.facility_id)
            if facility is None or facility.status == FacilityStatus.archived:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Structure sélectionnée introuvable dans le référentiel.",
                )
        elif payload.requested_facility_name:
            facility = HealthcareFacility(
                name=payload.requested_facility_name.strip()[:255],
                region=payload.region,
                district=payload.district,
                source=f"Demande à l'inscription ({payload.email})",
                source_type=RegistrySourceType.manual,
                status=FacilityStatus.pending_verification,
            )
            db.add(facility)
            db.flush()
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Sélectionnez votre structure de santé, ou demandez sa vérification "
                "si elle n'apparaît pas dans le référentiel.",
            )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=role,
        organization_id=org.id if org else None,
    )
    db.add(user)
    db.flush()

    if role in PROFESSIONAL_ROLES:
        prof = Professional(
            user_id=user.id,
            profession=payload.profession or payload.role,
            specialty=payload.specialty,
            license_number=payload.license_number,
            organization_id=org.id if org else None,
            verification_status=VerificationStatus.pending,
            verification_level=VerificationLevel.unverified,
        )
        db.add(prof)
        db.flush()
        db.add(VerificationRequest(professional_id=prof.id))

        if facility is not None:
            verification.request_affiliation(
                db, prof, facility, role_function=payload.role_function
            )
        # Duplicate detection: informational, never auto-resolved.
        verification.flag_duplicates(db, prof)

    db.commit()
    db.refresh(user)

    audit.log_action(
        db,
        action=audit.AuditAction.REGISTER,
        actor=user,
        resource_type="user",
        resource_id=user.id,
        ip=meta.get("ip"),
        user_agent=meta.get("user_agent"),
    )

    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        audit.log_action(
            db,
            action="login_failed",
            actor=None,
            resource_type="user",
            resource_id=None,
            meta={"email": payload.email},
            ip=meta.get("ip"),
            user_agent=meta.get("user_agent"),
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Compte désactivé")

    # MFA is enforced: when enabled, a valid TOTP code is mandatory. A missing or
    # wrong code never yields a token.
    if user.mfa_enabled:
        if not payload.mfa_code:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Code de vérification à deux facteurs requis",
            )
        if not user.mfa_secret or not pyotp.TOTP(user.mfa_secret).verify(
            payload.mfa_code, valid_window=1
        ):
            audit.log_action(
                db,
                action="login_failed",
                actor=user,
                resource_type="user",
                resource_id=user.id,
                meta={"reason": "mfa_invalid"},
                ip=meta.get("ip"),
                user_agent=meta.get("user_agent"),
            )
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Code à deux facteurs invalide"
            )

    audit.log_action(
        db,
        action=audit.AuditAction.LOGIN,
        actor=user,
        resource_type="user",
        resource_id=user.id,
        ip=meta.get("ip"),
        user_agent=meta.get("user_agent"),
    )

    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Jeton de rafraîchissement invalide"
        ) from None
    if data.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Type de jeton invalide")
    user = db.get(User, data.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Compte introuvable")
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/logout")
def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    audit.log_action(
        db,
        action=audit.AuditAction.LOGOUT,
        actor=user,
        resource_type="user",
        resource_id=user.id,
        ip=meta.get("ip"),
    )
    return {"detail": "Déconnecté"}


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prof = db.query(Professional).filter(Professional.user_id == user.id).first()
    out = MeOut.model_validate(user)
    if prof:
        out.professional = ProfessionalOut.model_validate(prof)
        level = prof.verification_level
        out.professional.verification_level = level.value
        out.professional.badge = verification.badge(level)
        out.professional.access_tier = verification.access_tier(level)
    return out


@router.post("/mfa/enable")
def mfa_enable(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a TOTP secret. MFA is opt-in and only enabled once confirmed."""
    secret = pyotp.random_base32()
    user.mfa_secret = secret
    db.commit()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="SunuDoctor")
    return {"secret": secret, "otpauth_url": uri, "enabled": False}


@router.post("/mfa/confirm")
def mfa_confirm(
    code: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.mfa_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "MFA non initialisé")
    if not pyotp.TOTP(user.mfa_secret).verify(code, valid_window=1):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Code invalide")
    user.mfa_enabled = True
    db.commit()
    return {"enabled": True}
