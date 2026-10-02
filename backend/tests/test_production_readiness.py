"""Production-readiness tests: config guards and database migrations.

These ensure the platform refuses to run an unsafe production configuration and
that the migration chain produces the full schema.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.core.config import Settings

BACKEND = Path(__file__).resolve().parents[1]


def _settings(**kw) -> Settings:
    base = {
        "environment": "production",
        "secret_key": "x" * 40,
        "database_url": "postgresql+psycopg://u:p@db:5432/sunudoctor",
        "ai_mode": "demo",
        "payment_mode": "demo",
        "_env_file": None,
    }
    base.update(kw)
    return Settings(**base)


def test_safe_production_config_has_no_problems():
    assert _settings().production_problems() == []


def test_default_secret_is_rejected_in_production():
    problems = _settings(secret_key="dev-only-insecure-change-me").production_problems()
    assert any("SECRET_KEY" in p for p in problems)


def test_short_secret_is_rejected_in_production():
    assert any("SECRET_KEY" in p for p in _settings(secret_key="short").production_problems())


def test_sqlite_is_rejected_in_production():
    problems = _settings(database_url="sqlite:///./x.db").production_problems()
    assert any("PostgreSQL" in p for p in problems)


def test_live_ai_without_keys_is_rejected():
    problems = _settings(ai_mode="live", clinical_ai_provider="openai").production_problems()
    assert any("OPENAI_API_KEY" in p for p in problems)


def test_live_payments_without_provider_is_rejected():
    problems = _settings(payment_mode="live").production_problems()
    assert any("fournisseur" in p for p in problems)


def test_live_payments_without_webhook_secret_is_rejected():
    problems = _settings(
        payment_mode="live", wave_api_key="real-key", wave_webhook_secret=""
    ).production_problems()
    assert any("webhook" in p for p in problems)


def test_migration_chain_creates_full_schema(tmp_path):
    """`alembic upgrade head` must create every table (not just alembic_version)."""
    db = tmp_path / "mig.db"
    env = {
        "DATABASE_URL": f"sqlite:///{db}",
        "SECRET_KEY": "migration-test-secret-key-at-least-32-chars",
    }
    import os

    full_env = {**os.environ, **env}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env=full_env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    import sqlite3

    con = sqlite3.connect(db)
    tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    con.close()
    # A representative set of clinical + billing tables must exist.
    for expected in {
        "users",
        "patients",
        "consultations",
        "ai_transcriptions",
        "ai_structured_notes",
        "subscriptions",
        "payments",
        "webhook_events",
        "audit_logs",
        "signaling_messages",
    }:
        assert expected in tables, f"table manquante après migration: {expected}"
    assert len(tables) > 20
