"""Billing: plans, subscriptions and payments.

Billing data is fully separated from clinical data. An unpaid subscription never
deletes or modifies a clinical record.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_meta, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import Payment, Subscription, User
from app.schemas import PaymentRequest, SubscribeRequest
from app.services import audit
from app.services.billing import pricing, webhooks
from app.services.billing.providers import get_provider, list_providers

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans")
def get_plans():
    return {
        "label": "Tarifs de lancement",
        "disclaimer": "Tarifs de lancement. Ne correspondent pas à une étude de marché officielle.",
        "trial_days": settings.trial_days,
        "plans": pricing.as_dicts(),
    }


@router.get("/providers")
def get_payment_providers():
    return {
        "mode": settings.payment_mode,
        "providers": list_providers(),
        "notice": "Les paiements réels nécessitent une configuration côté serveur. "
        "En mode démonstration, aucun paiement n'est effectué.",
    }


@router.post("/subscribe", status_code=201)
def subscribe(
    payload: SubscribeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = pricing.PLANS_BY_CODE.get(payload.plan_code)
    if plan is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Plan inconnu")
    now = datetime.now(UTC)
    sub = Subscription(
        owner_user_id=user.id,
        organization_id=user.organization_id,
        plan_code=plan.code,
        plan_label=plan.label,
        price_fcfa=plan.price_fcfa,
        status="trial",
        trial_ends_at=now + timedelta(days=settings.trial_days),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {
        "id": sub.id,
        "plan_code": sub.plan_code,
        "plan_label": sub.plan_label,
        "price_fcfa": sub.price_fcfa,
        "status": sub.status,
        "trial_ends_at": sub.trial_ends_at,
        "notice": f"{settings.trial_days} jours d'essai — aucune donnée clinique n'est affectée par la facturation.",
    }


@router.get("/subscription")
def my_subscription(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = (
        db.query(Subscription)
        .filter(Subscription.owner_user_id == user.id)
        .order_by(Subscription.created_at.desc())
        .first()
    )
    if sub is None:
        return {"subscription": None, "notice": "Aucun abonnement actif."}
    return {
        "subscription": {
            "id": sub.id,
            "plan_code": sub.plan_code,
            "plan_label": sub.plan_label,
            "price_fcfa": sub.price_fcfa,
            "status": sub.status,
            "trial_ends_at": sub.trial_ends_at,
        }
    }


@router.post("/payments", status_code=201)
def create_payment(
    payload: PaymentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = db.get(Subscription, payload.subscription_id)
    if sub is None or sub.owner_user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Abonnement introuvable")
    provider = get_provider(payload.provider)
    intent = provider.create_payment(sub.price_fcfa)
    # A payment is ALWAYS created pending: success only comes from a verified
    # server-side webhook. The browser can never assert success.
    payment = Payment(
        subscription_id=sub.id,
        provider=intent.provider,
        provider_ref=intent.reference,
        idempotency_key=f"{intent.provider}:{intent.reference}",
        amount_fcfa=intent.amount_fcfa,
        status=intent.status,
        is_demo=intent.is_demo,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    audit.log_action(
        db,
        action=audit.AuditAction.PAYMENT_CREATE,
        actor=user,
        resource_type="payment",
        resource_id=payment.id,
        meta={"provider": payment.provider, "is_demo": payment.is_demo},
    )
    return {
        "id": payment.id,
        "provider": payment.provider,
        "reference": payment.provider_ref,
        "amount_fcfa": payment.amount_fcfa,
        "status": payment.status,
        "is_demo": payment.is_demo,
        "message": intent.message,
        "notice": "Un paiement n'est confirmé qu'après vérification serveur (webhook signé).",
    }


@router.post("/webhooks/{provider_code}", include_in_schema=True)
async def payment_webhook(
    provider_code: str,
    request: Request,
    db: Session = Depends(get_db),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
):
    """Receive a provider payment webhook.

    The raw body is read verbatim so the signature can be verified byte for
    byte. Unsigned webhooks are recorded but never applied. Duplicate events are
    ignored (idempotency). This endpoint is unauthenticated by necessity but is
    fully protected by signature verification and idempotency.
    """
    raw = await request.body()
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payload invalide") from None
    if not isinstance(payload, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payload invalide")
    result = webhooks.process_webhook(
        db,
        provider_code=provider_code,
        raw_body=raw,
        signature=x_signature,
        payload=payload,
    )
    # Always 200 so the provider does not retry a permanently invalid payload;
    # the recorded event carries the truth.
    return result


@router.get("/payments")
def list_my_payments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subs = db.query(Subscription).filter(Subscription.owner_user_id == user.id).all()
    sub_ids = [s.id for s in subs]
    if not sub_ids:
        return []
    payments = (
        db.query(Payment)
        .filter(Payment.subscription_id.in_(sub_ids))
        .order_by(Payment.created_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "provider": p.provider,
            "reference": p.provider_ref,
            "amount_fcfa": p.amount_fcfa,
            "status": p.status,
            "is_demo": p.is_demo,
            "confirmed_at": p.confirmed_at,
            "created_at": p.created_at,
        }
        for p in payments
    ]


@router.post("/payments/{payment_id}/reconcile")
def reconcile_payment(
    payment_id: str,
    state: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    """Manual reconciliation of a bank transfer by an operator.

    Restricted to the subscription owner for demonstration purposes; in
    production this is an operator-only action. It never touches clinical data.
    """
    from app.services.billing import providers as pay

    if state not in pay.VALID_STATES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "État de paiement invalide")
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paiement introuvable")
    sub = db.get(Subscription, payment.subscription_id) if payment.subscription_id else None
    if sub is None or sub.owner_user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Non autorisé")
    payment.status = state
    if state == pay.SUCCESS:
        payment.confirmed_at = datetime.now(UTC)
        sub.status = "active"
        sub.current_period_end = datetime.now(UTC) + timedelta(days=30)
    db.commit()
    audit.log_action(
        db,
        action="payment_reconcile",
        actor=user,
        resource_type="payment",
        resource_id=payment.id,
        meta={"state": state},
        ip=meta.get("ip"),
    )
    return {"id": payment.id, "status": payment.status}
