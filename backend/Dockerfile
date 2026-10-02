# SunuDoctor backend — production image.
#
# Build context: ./backend
#   docker build -t sunudoctor-api ./backend
#
# Security notes:
# - Multi-stage build; the runtime image carries no build tooling.
# - Runs as an unprivileged user (uid 10001).
# - No secret is baked in: every secret comes from the environment at runtime.
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=production

# Unprivileged runtime user.
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app app ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini ./alembic.ini
COPY --chown=app:app entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

USER app
EXPOSE 8000

# Liveness probe target; the app also exposes /api/health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status==200 else 1)"

# Apply migrations, then serve. Migrations are idempotent (alembic is safe to
# run on every boot).
ENTRYPOINT ["./entrypoint.sh"]
