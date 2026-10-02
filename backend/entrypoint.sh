#!/bin/sh
# SunuDoctor backend entrypoint.
#
# 1. Wait for the database to accept connections.
# 2. Apply pending migrations (idempotent).
# 3. Exec the API server so it becomes PID 1 and receives signals correctly.
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"

echo "Applying database migrations…"
python -m alembic upgrade head

echo "Starting SunuDoctor API…"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips "*"
