"""Shared FastAPI dependencies: current user, role guards, request metadata."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import decode_token
from app.models.entities import Role, User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise")
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Jeton invalide ou expiré"
        ) from None
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Type de jeton invalide")
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Compte introuvable ou inactif")
    return user


def require_roles(*roles: Role):
    def guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permission refusée")
        return user

    return guard


def require_verified_professional(user: User = Depends(get_current_user)) -> User:
    """Require a professional whose identity has actually been verified.

    A non-verified account keeps a limited account: it can prepare a profile and
    submit documents, but it cannot author clinical content. Verification is
    never automatic; see app.services.verification.
    """
    from app.core.config import settings
    from app.models.entities import Professional
    from app.services import verification

    if not settings.require_verified_professional:
        return user
    if user.role in {Role.platform_admin, Role.verification_officer}:
        return user
    db = SessionLocal()
    try:
        prof = db.query(Professional).filter(Professional.user_id == user.id).first()
        if prof is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Profil professionnel requis pour cette action.",
            )
        if not verification.can_author_clinical(prof.verification_level):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Vérification professionnelle requise avant de documenter des soins. "
                "Statut actuel : "
                + verification.LEVEL_LABELS.get(
                    prof.verification_level, prof.verification_level.value
                ),
            )
    finally:
        db.close()
    return user


def request_meta(request: Request) -> dict:
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


def get_client_meta(
    request: Request,
    x_forwarded_for: str | None = Header(default=None, alias="X-Forwarded-For"),
) -> dict:
    ip = None
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    elif request.client:
        ip = request.client.host
    return {"ip": ip, "user_agent": request.headers.get("user-agent")}
