"""Administration API tests: separation of duties and LOT 3 admin endpoints.

Administration must never grant automatic access to clinical content, and the
billing/support/audit surfaces must be complete for operations.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_admin_endpoints_reject_non_admin(client, doctor):
    _, headers = doctor
    for path in (
        "/api/admin/payments",
        "/api/admin/payments/summary",
        "/api/admin/support/tickets",
        "/api/admin/audit/export",
        "/api/admin/users",
    ):
        r = client.get(path, headers=headers)
        assert r.status_code == 403, f"{path} should be admin-only, got {r.status_code}"


def test_payments_summary_reports_demo_separately(client, admin):
    _, headers = admin
    r = client.get("/api/admin/payments/summary", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "by_status" in body
    assert "demo_payments" in body
    assert "synth" in body["notice"].lower() or "demo" in body["notice"].lower()


def test_payments_list_is_billing_only(client, admin):
    _, headers = admin
    r = client.get("/api/admin/payments", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_support_ticket_missing_returns_404(client, admin):
    _, headers = admin
    r = client.get("/api/admin/support/tickets", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = client.post(
        "/api/admin/support/tickets/does-not-exist/status?new_status=open", headers=headers
    )
    assert r.status_code == 404


def test_audit_export_is_itself_audited(client, admin):
    _, headers = admin
    r = client.get("/api/admin/audit/export", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "count" in body and "entries" in body

    r2 = client.get("/api/admin/audit?action=export", headers=headers)
    assert r2.status_code == 200
    assert any(e["action"] == "export" for e in r2.json())


def test_admin_config_never_exposes_secrets(client, admin):
    _, headers = admin
    r = client.get("/api/admin/config", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body.get("secrets_exposed") is False
    flat = str(body).lower()
    for banned in ("secret_key", "api_key", "password", "token"):
        assert banned not in flat
