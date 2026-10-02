"""Registry provider interfaces.

These are pure interfaces: they describe how SunuDoctor would talk to an
authorised facility referential. They contain no credentials, no endpoints and
no assumption that any service is reachable.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderInfo:
    """Honest status of a registry provider.

    ``connected`` is True only when the provider is both selected and actually
    usable (endpoint + credential). It is never inferred from configuration
    alone.
    """

    name: str
    requested: str
    connected: bool
    reason: str
    source_type: str


@dataclass
class FacilityRecord:
    """Normalised facility record, independent of the source format."""

    name: str
    type: str = "OTHER"
    region: str | None = None
    district: str | None = None
    commune: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    email: str | None = None
    short_name: str | None = None
    official_id: str | None = None
    source: str | None = None
    source_type: str = "MANUAL"
    status: str = "PENDING_VERIFICATION"
    extra: dict = field(default_factory=dict)


class HealthRegistryProvider:
    """Base class for all registry providers."""

    name = "base"
    source_type = "MANUAL"

    def info(self) -> ProviderInfo:  # pragma: no cover - interface
        raise NotImplementedError

    def is_connected(self) -> bool:
        return self.info().connected

    def search(
        self,
        query: str,
        *,
        region: str | None = None,
        district: str | None = None,
        facility_type: str | None = None,
        limit: int = 20,
    ) -> list[FacilityRecord]:  # pragma: no cover - interface
        raise NotImplementedError

    def fetch_by_official_id(self, official_id: str) -> FacilityRecord | None:
        return None
