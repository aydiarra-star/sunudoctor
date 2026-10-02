"""Payment provider abstraction.

Secret keys remain server-side only. When a provider has no real credentials,
``is_connected`` is False and the provider operates in DEMONSTRATION mode: it
returns a clearly labelled demo reference and never claims a real payment.

An unpaid subscription NEVER deletes or alters clinical data: clinical and
billing data are fully separated in the schema.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class PaymentIntent:
    provider: str
    reference: str
    amount_fcfa: int
    currency: str = "XOF"
    status: str = "pending"
    is_demo: bool = True
    checkout_url: str | None = None
    message: str = ""


class PaymentProvider(ABC):
    name: str = "abstract"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    @property
    def is_connected(self) -> bool:
        return bool(self.api_key) and settings.payment_mode == "live"

    @abstractmethod
    def create_payment(self, amount_fcfa: int, *, reference: str | None = None) -> PaymentIntent:
        ...

    def _demo_intent(self, amount_fcfa: int, reference: str | None) -> PaymentIntent:
        ref = reference or f"DEMO-{uuid.uuid4().hex[:12].upper()}"
        return PaymentIntent(
            provider=self.name,
            reference=ref,
            amount_fcfa=amount_fcfa,
            is_demo=True,
            status="pending",
            message="Mode démonstration — aucun paiement réel n'est effectué.",
        )


class WaveProvider(PaymentProvider):
    name = "wave"

    def create_payment(self, amount_fcfa, *, reference=None):
        if not self.is_connected:
            return self._demo_intent(amount_fcfa, reference)
        raise NotImplementedError("Configuration Wave requise pour les paiements réels.")


class OrangeMoneyProvider(PaymentProvider):
    name = "orange_money"

    def create_payment(self, amount_fcfa, *, reference=None):
        if not self.is_connected:
            return self._demo_intent(amount_fcfa, reference)
        raise NotImplementedError("Configuration Orange Money requise pour les paiements réels.")


class CardProvider(PaymentProvider):
    name = "card"

    def create_payment(self, amount_fcfa, *, reference=None):
        if not self.is_connected:
            return self._demo_intent(amount_fcfa, reference)
        raise NotImplementedError("Configuration du fournisseur carte requise.")


class BankProvider(PaymentProvider):
    name = "bank"

    def create_payment(self, amount_fcfa, *, reference=None):
        return self._demo_intent(amount_fcfa, reference)


class OtherProvider(PaymentProvider):
    name = "other"

    def create_payment(self, amount_fcfa, *, reference=None):
        return self._demo_intent(amount_fcfa, reference)


def get_provider(code: str) -> PaymentProvider:
    providers = {
        "wave": WaveProvider(settings.wave_api_key),
        "orange_money": OrangeMoneyProvider(settings.orange_money_api_key),
        "card": CardProvider(settings.card_provider_api_key),
        "bank": BankProvider(),
        "other": OtherProvider(),
    }
    return providers.get(code, OtherProvider())


def list_providers() -> list[dict]:
    return [
        {"code": "wave", "label": "Wave", "connected": WaveProvider(settings.wave_api_key).is_connected},
        {"code": "orange_money", "label": "Orange Money", "connected": OrangeMoneyProvider(settings.orange_money_api_key).is_connected},
        {"code": "card", "label": "Carte bancaire", "connected": CardProvider(settings.card_provider_api_key).is_connected},
        {"code": "bank", "label": "Virement", "connected": False},
        {"code": "other", "label": "Autre", "connected": False},
    ]
