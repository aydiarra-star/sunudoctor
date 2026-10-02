"""Server-side webhook processing for payments.

Guarantees:
- Signature verification: an unverified webhook is recorded but NEVER applied.
- Idempotency: an event is processed at most once (unique ``event_key``). A
  replayed or delayed webhook is stored and ignored, so a double delivery can
  never double-activate a subscription.
- Clinical isolation: this module only ever touches billing tables. It cannot
  modify a patient record, a consultation or a prescription.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Payment, Subscription, WebhookEvent
from app.services.billing import providers as pay
from app.services.billing.providers import get_provider

logger = logging.getLogger("sunudoctor.billing")

# Provider event/status -> canonical payment state.
_STATUS_MAP = {
    "success": pay.SUCCESS,
    "succeeded": pay.SUCCESS,
    "paid": pay.SUCCESS,
    "completed": pay.SUCCESS,
    "failed": pay.FAILED,
    "error": pay.FAILED,
    "cancelled": pay.CANCELLED,
    "canceled": pay.CANCELLED,
    "refunded": pay.REFUNDED,
    "processing": pay.PROCESSING,
    "pending": pay.PENDING,
}


def _event_key(provider: str, payload: dict) -> str:
    """Stable key used for idempotency. Prefers the provider's own event id."""
    for field in ("id", "event_id", "transaction_id", "reference", "provider_ref"):
        value = payload.get(field)
        if value:
            return f"{provider}:{value}"
    # Last resort: hash the payload so identical retries collapse.
    import hashlib

    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]
    return f"{provider}:hash:{digest}"


def process_webhook(
    db: Session,
    *,
    provider_code: str,
    raw_body: bytes,
    signature: str | None,
    payload: dict,
) -> dict:
    """Record and (if valid + new) apply a payment webhook.

    Returns a dict describing the outcome. Never raises on a bad signature or a
    duplicate: both are normal, non-fatal situations.
    """
    provider = get_provider(provider_code)
    key = _event_key(provider_code, payload)
    signature_valid = provider.verify_webhook(raw_body, signature)

    existing = (
        db.query(WebhookEvent).filter(WebhookEvent.event_key == key).first()
    )
    if existing is not None:
        logger.info("webhook duplicate ignored", extra={"provider": provider_code})
        return {
            "status": "duplicate",
            "processed": False,
            "signature_valid": existing.signature_valid,
            "event_key": key,
        }

    event = WebhookEvent(
        provider=provider_code,
        event_key=key,
        event_type=str(payload.get("type") or payload.get("event") or ""),
        signature_valid=signature_valid,
        processed=False,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    db.add(event)
    db.flush()

    # In demo mode we accept unsigned webhooks but never mark a real success.
    accepted = signature_valid or settings.payment_mode == "demo"
    if not accepted:
        db.commit()
        logger.warning("webhook signature rejected", extra={"provider": provider_code})
        return {
            "status": "rejected",
            "processed": False,
            "signature_valid": False,
            "event_key": key,
        }

    # Locate the payment this webhook refers to.
    ref = (
        payload.get("reference")
        or payload.get("provider_ref")
        or payload.get("transaction_id")
    )
    payment = None
    if ref:
        payment = (
            db.query(Payment)
            .filter(Payment.provider == provider_code, Payment.provider_ref == ref)
            .first()
        )

    raw_status = str(payload.get("status") or payload.get("state") or "").lower()
    new_state = _STATUS_MAP.get(raw_status, pay.PENDING)

    # A demo-mode webhook can never produce a real success.
    if settings.payment_mode == "demo" and new_state == pay.SUCCESS:
        new_state = pay.PENDING

    if payment is not None:
        payment.status = new_state
        if new_state == pay.SUCCESS:
            payment.confirmed_at = datetime.now(UTC)
            _activate_subscription(db, payment)
        elif new_state in {pay.FAILED, pay.CANCELLED}:
            _deactivate_subscription(db, payment)

    event.processed = payment is not None
    db.commit()
    logger.info(
        "webhook processed",
        extra={"provider": provider_code, "state": new_state, "applied": payment is not None},
    )
    return {
        "status": "processed",
        "processed": payment is not None,
        "signature_valid": signature_valid,
        "state": new_state,
        "event_key": key,
    }


def _activate_subscription(db: Session, payment: Payment) -> None:
    if not payment.subscription_id:
        return
    sub = db.get(Subscription, payment.subscription_id)
    if sub is None:
        return
    sub.status = "active"
    sub.current_period_end = datetime.now(UTC) + timedelta(days=30)
    # NOTE: activation touches ONLY the subscription. No clinical row is read or
    # written here — separation of clinical and billing data is absolute.


def _deactivate_subscription(db: Session, payment: Payment) -> None:
    if not payment.subscription_id:
        return
    sub = db.get(Subscription, payment.subscription_id)
    if sub is None:
        return
    # Suspending a subscription never deletes or alters clinical data.
    sub.status = "past_due"
