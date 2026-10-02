"""Billing: plans, subscriptions and payments.

Billing data is fully separated from clinical data. An unpaid subscription never
deletes or modifies a clinical record.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import Payment, Subscription, User
from app.schemas import PaymentRequest, SubscribeRequest
from app.services import audit
from app.services.billing import pricing
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
    payment = Payment(
        subscription_id=sub.id,
        provider=intent.provider,
        provider_ref=intent.reference,
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
    }
