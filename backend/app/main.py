"""SunuDoctor API — application entrypoint.

Security middleware applied globally:
- CORS restricted to configured origins
- security headers (XSS, clickjacking, MIME sniffing, HSTS)
- per-IP rate limiting on sensitive endpoints
"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import admin, auth, billing, clinical, coordination, patients, scribe
from app.core.config import settings
from app.core.database import Base, engine

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Plateforme de santé numérique pour le Sénégal. Scribe clinique multilingue "
        "(Wolof + Français), dossier patient, téléconsultation, coordination des soins."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# --- Simple in-memory rate limiter (per IP, per window) ---
_hits: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Rate limiting for auth endpoints.
    if request.url.path.startswith(("/api/auth", "/api/billing")):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        _hits[ip] = [t for t in _hits[ip] if now - t < settings.rate_limit_window]
        if len(_hits[ip]) >= settings.rate_limit_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Trop de requêtes. Veuillez réessayer plus tard."},
            )
        _hits[ip].append(now)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(self)"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "ai_mode": settings.ai_mode,
        "payment_mode": settings.payment_mode,
    }


@app.get("/api/meta")
def meta():
    """Public, non-sensitive metadata used by the frontend to be honest about
    which capabilities are real vs demonstration."""
    return {
        "app": "SunuDoctor",
        "ai_mode": settings.ai_mode,
        "payment_mode": settings.payment_mode,
        "demo_banner": "Mode démonstration" if settings.ai_mode == "demo" else None,
        "capabilities": {
            "clinical_scribe_pipeline": "demo",
            "wolof_speech_to_text": "non_connecte",
            "clinical_structuring": "demo",
            "translation": "demo",
            "teleconsultation_video": "configuration_requise",
            "payments": "demo" if settings.payment_mode == "demo" else "live",
        },
    }


app.include_router(auth.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(scribe.router, prefix="/api")
app.include_router(clinical.router, prefix="/api")
app.include_router(coordination.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
