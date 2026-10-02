"""SunuDoctor API — application entrypoint.

Security middleware applied globally:
- CORS restricted to configured origins
- security headers (XSS, clickjacking, MIME sniffing, HSTS)
- per-IP rate limiting on sensitive endpoints
"""
from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, auth, billing, clinical, coordination, patients, scribe
from app.core.config import settings
from app.core.database import Base, engine
from app.core.observability import (
    configure_logging,
    correlation_id,
    logger,
    metrics,
    new_correlation_id,
)

configure_logging()

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
    # Correlation id: reuse an inbound one (behind a proxy) or create a new one.
    incoming = request.headers.get("X-Request-ID")
    cid = incoming if incoming else new_correlation_id()
    correlation_id.set(cid)

    # Rate limiting for auth endpoints.
    if request.url.path.startswith(("/api/auth", "/api/billing")):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        _hits[ip] = [t for t in _hits[ip] if now - t < settings.rate_limit_window]
        if len(_hits[ip]) >= settings.rate_limit_requests:
            metrics.incr("rate_limited")
            return JSONResponse(
                status_code=429,
                content={"detail": "Trop de requêtes. Veuillez réessayer plus tard."},
                headers={"X-Request-ID": cid},
            )
        _hits[ip].append(now)

    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(self)"
    response.headers["X-Request-ID"] = cid
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Metrics + structured access log (no clinical content, no body).
    metrics.incr(f"http_{response.status_code}")
    metrics.observe(f"{request.method} {request.url.path}", duration_ms)
    logger.info(
        "request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
        },
    )
    return response


@app.on_event("startup")
def on_startup() -> None:
    # In production the schema is managed by migrations (alembic upgrade head),
    # never by create_all. create_all is kept for local dev and tests only, so a
    # fresh developer checkout still works with zero setup.
    problems = settings.production_problems()
    if problems:
        if settings.is_production:
            # Fail fast: a misconfigured production instance must not start and
            # silently serve demo output as if it were real.
            raise RuntimeError(
                "Configuration de production invalide:\n- " + "\n- ".join(problems)
            )
        logger.warning("production readiness warnings: %s", "; ".join(problems))
    if not settings.is_production:
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


@app.get("/api/metrics")
def get_metrics():
    """Operational metrics. Contains no clinical content and no secrets."""
    return metrics.snapshot()


@app.get("/api/meta")
def meta():
    """Public, non-sensitive metadata used by the frontend to be honest about
    which capabilities are real vs demonstration.

    ``providers`` is derived from the same capability helpers the factory uses,
    so this endpoint can never claim a service is connected when it is not.
    """
    from app.services.ai.factory import provider_status

    status = provider_status()
    return {
        "app": "SunuDoctor",
        "ai_mode": settings.ai_mode,
        "payment_mode": settings.payment_mode,
        "demo_banner": "Mode démonstration" if settings.ai_mode == "demo" else None,
        "providers": status,
        "capabilities": {
            "clinical_scribe_pipeline": "live" if status["clinical_ai"]["connected"] else "demo",
            "wolof_speech_to_text": (
                "live" if status["stt"]["connected"] else "non_connecte"
            ),
            "clinical_structuring": (
                "live" if status["clinical_ai"]["connected"] else "demo"
            ),
            "translation": "live" if status["translation"]["connected"] else "demo",
            "teleconsultation_video": (
                "live" if settings.turn_configured else "configuration_requise"
            ),
            "payments": (
                "live"
                if any(settings.payment_provider_configured.values())
                else ("demo" if settings.payment_mode == "demo" else "configuration_requise")
            ),
        },
    }


app.include_router(auth.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(scribe.router, prefix="/api")
app.include_router(clinical.router, prefix="/api")
app.include_router(coordination.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


# --- Optional static serving of the built frontend (single-origin deploys) ---
# When FRONTEND_DIST points at a built frontend, the API also serves the SPA so
# the whole product runs behind one public URL. API routes keep precedence
# because they are registered above.
_frontend_dist = Path(settings.frontend_dist) if settings.frontend_dist else None
if _frontend_dist and _frontend_dist.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_frontend_dist / "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        candidate = _frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_frontend_dist / "index.html")
