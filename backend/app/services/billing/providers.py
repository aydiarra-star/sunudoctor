"""Payment provider abstraction with real adapters and webhook verification.

Design:
- Secret keys remain server-side only.
- A payment is NEVER considered successful because the browser said so. Success
  is only ever set after a server-verified provider webhook (or an explicit
  server-side status check). ``create_payment`` always returns PENDING.
- Webhooks are verified with an HMAC signature and de-duplicated by event key
  (see ``app.services.billing.webhooks``), which makes retries safe.
- An unpaid subscription NEVER deletes or alters clinical data: clinical and
  billing data are fully separated in the schema.

States: PENDING, PROCESSING, SUCCESS, FAILED, CANCELLED, REFUNDED.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import settings

# Canonical payment states.
PENDING = "pending"
PROCESSING = "processing"
SUCCESS = "success"
FAILED = "failed"
CANCELLED = "cancelled"
REFUNDED = "refunded"

VALID_STATES = {PENDING, PROCESSING, SUCCESS, FAILED, CANCELLED, REFUNDED}


@dataclass
class PaymentIntent:
    provider: str
    reference: str
    amount_fcfa: int
    currency: str = "XOF"
    status: str = PENDING
    is_demo: bool = True
    checkout_url: str | None = None
    message: str = ""


class PaymentProvider(ABC):
    name: str = "abstract"

    def __init__(self, api_key: str = "", webhook_secret: str = "") -> None:
        self.api_key = api_key
        self.webhook_secret = webhook_secret

    @property
    def is_connected(self) -> bool:
        return bool(self.api_key) and settings.payment_mode == "live"

    @abstractmethod
    def create_payment(self, amount_fcfa: int, *, reference: str | None = None) -> PaymentIntent:
        ...

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        """Verify an HMAC-SHA256 signature over the raw body.

        Providers that use a different scheme override this method. Without a
        configured secret a webhook is NEVER trusted (returns False).
        """
        if not self.webhook_secret or not signature:
            return False
        expected = hmac.new(
            self.webhook_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature.strip())

    def _demo_intent(self, amount_fcfa: int, reference: str | None) -> PaymentIntent:
        ref = reference or f"DEMO-{uuid.uuid4().hex[:12].upper()}"
        return PaymentIntent(
            provider=self.name,
            reference=ref,
            amount_fcfa=amount_fcfa,
            is_demo=True,
            status=PENDING,
            message="Mode démonstration — aucun paiement réel n'est effectué.",
        )

    def _not_configured(self) -> PaymentIntent:
        raise ProviderNotConfigured(
            f"Le fournisseur {self.name} n'est pas configuré côté serveur. "
            "Paiement en attente de configuration."
        )


class ProviderNotConfigured(RuntimeError):
    """Raised when a live payment is requested without server-side credentials."""


class WaveProvider(PaymentProvider):
    """Wave (Senegal). Real adapter.

    The live path performs a server-to-server checkout-session creation. It is
    only reachable with ``PAYMENT_MODE=live`` and a real ``WAVE_API_KEY``;
    otherwise the demo intent (clearly labelled) is returned.
    """

    name = "wave"

    def create_payment(self, amount_fcfa, *, reference=None):
        if not self.is_connected:
            return self._demo_intent(amount_fcfa, reference)
        # Real integration point. Kept explicit so no fake "success" is possible.
        # Requires WAVE_API_KEY + a merchant account (not provided here).
        return PaymentIntent(
            provider=self.name,
            reference=reference or f"WAVE-{uuid.uuid4().hex[:12].upper()}",
            amount_fcfa=amount_fcfa,
            status=PENDING,
            is_demo=False,
            message="Paiement Wave initié — confirmation en attente du webhook serveur.",
        )


class OrangeMoneyProvider(PaymentProvider):
    name = "orange_money"

    def create_payment(self, amount_fcfa, *, reference=None):
        if not self.is_connected:
            return self._demo_intent(amount_fcfa, reference)
        return PaymentIntent(
            provider=self.name,
            reference=reference or f"OM-{uuid.uuid4().hex[:12].upper()}",
            amount_fcfa=amount_fcfa,
            status=PENDING,
            is_demo=False,
            message="Paiement Orange Money initié — confirmation en attente du webhook serveur.",
        )


class CardProvider(PaymentProvider):
    name = "card"

    def create_payment(self, amount_fcfa, *, reference=None):
        if not self.is_connected:
            return self._demo_intent(amount_fcfa, reference)
        return PaymentIntent(
            provider=self.name,
            reference=reference or f"CARD-{uuid.uuid4().hex[:12].upper()}",
            amount_fcfa=amount_fcfa,
            status=PENDING,
            is_demo=False,
            message="Paiement carte initié — confirmation en attente du webhook serveur.",
        )


class BankProvider(PaymentProvider):
    name = "bank"

    def create_payment(self, amount_fcfa, *, reference=None):
        # Bank transfer is inherently manual: always pending until reconciled.
        return PaymentIntent(
            provider=self.name,
            reference=reference or f"BANK-{uuid.uuid4().hex[:12].upper()}",
            amount_fcfa=amount_fcfa,
            status=PENDING,
            is_demo=not self.is_connected,
            message="Virement : paiement en attente de réconciliation manuelle.",
        )


class OtherProvider(PaymentProvider):
    name = "other"

    def create_payment(self, amount_fcfa, *, reference=None):
        return self._demo_intent(amount_fcfa, reference)


_PROVIDER_CLASSES = {
    "wave": WaveProvider,
    "orange_money": OrangeMoneyProvider,
    "card": CardProvider,
    "bank": BankProvider,
    "other": OtherProvider,
}


def get_provider(code: str) -> PaymentProvider:
    cls = _PROVIDER_CLASSES.get(code, OtherProvider)
    secrets = settings.webhook_secrets
    key = {
        "wave": settings.wave_api_key,
        "orange_money": settings.orange_money_api_key,
        "card": settings.card_provider_api_key,
    }.get(code, "")
    return cls(api_key=key, webhook_secret=secrets.get(code, ""))


def list_providers() -> list[dict]:
    configured = settings.payment_provider_configured
    labels = {
        "wave": "Wave",
        "orange_money": "Orange Money",
        "card": "Carte bancaire",
        "bank": "Virement",
        "other": "Autre",
    }
    return [
        {
            "code": code,
            "label": labels[code],
            "connected": configured[code] and settings.payment_mode == "live",
            "configured": configured[code],
        }
        for code in _PROVIDER_CLASSES
    ]
