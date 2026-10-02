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
    Organization,
    Professional,
    Role,
    User,
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
from app.services import audit

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
        )
        db.add(prof)
        db.flush()
        db.add(VerificationRequest(professional_id=prof.id))

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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Compte désactivé")

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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton de rafraîchissement invalide")
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
    out.professional = ProfessionalOut.model_validate(prof) if prof else None
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
