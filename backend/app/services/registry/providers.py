"""Concrete registry providers.

Only the local provider is functional out of the box, because it operates on
data SunuDoctor actually holds. The official and partner providers are real
integration points that stay disconnected until an operator supplies an
authorised endpoint and credential. They never scrape or bypass a protected
system, and they never fabricate results.
"""
from __future__ import annotations

from app.core.config import settings
from app.models.entities import FacilityStatus, RegistrySourceType
from app.services.registry.base import (
    FacilityRecord,
    HealthRegistryProvider,
    ProviderInfo,
)


class LocalRegistryProvider(HealthRegistryProvider):
    """Reads the referential stored in SunuDoctor's own database.

    This is always connected: it reflects what SunuDoctor actually has, with the
    provenance recorded on each row. It does not claim any record is official.
    """

    name = "local"
    source_type = RegistrySourceType.manual.value

    def __init__(self, db):
        self.db = db

    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            requested="local",
            connected=True,
            reason="Référentiel interne SunuDoctor (provenance indiquée par entrée).",
            source_type=self.source_type,
        )

    def _to_record(self, facility) -> FacilityRecord:
        return FacilityRecord(
            name=facility.name,
            type=facility.type.value,
            region=facility.region,
            district=facility.district,
            commune=facility.commune,
            address=facility.address,
            latitude=facility.latitude,
            longitude=facility.longitude,
            phone=facility.phone,
            email=facility.email,
            short_name=facility.short_name,
            official_id=facility.official_id,
            source=facility.source,
            source_type=facility.source_type.value,
            status=facility.status.value,
        )

    def search(
        self,
        query: str,
        *,
        region: str | None = None,
        district: str | None = None,
        facility_type: str | None = None,
        limit: int = 20,
    ) -> list[FacilityRecord]:
        from app.models.entities import HealthcareFacility
        from app.services.matching import normalize_text

        q = self.db.query(HealthcareFacility).filter(
            HealthcareFacility.status != FacilityStatus.archived
        )
        if region:
            q = q.filter(HealthcareFacility.region == region)
        if district:
            q = q.filter(HealthcareFacility.district == district)
        if facility_type:
            q = q.filter(HealthcareFacility.type == facility_type)

        needle = normalize_text(query)
        rows = q.all()
        if not needle:
            rows.sort(key=lambda f: f.name)
            return [self._to_record(f) for f in rows[:limit]]

        scored = []
        for facility in rows:
            haystack = normalize_text(
                " ".join(filter(None, [facility.name, facility.short_name, facility.commune]))
            )
            if needle in haystack:
                scored.append((0 if haystack.startswith(needle) else 1, facility.name, facility))
        scored.sort(key=lambda t: (t[0], t[1]))
        return [self._to_record(f) for _, _, f in scored[:limit]]

    def fetch_by_official_id(self, official_id: str) -> FacilityRecord | None:
        from app.models.entities import HealthcareFacility

        facility = (
            self.db.query(HealthcareFacility)
            .filter(HealthcareFacility.official_id == official_id)
            .first()
        )
        return self._to_record(facility) if facility else None


class OfficialRegistryProvider(HealthRegistryProvider):
    """Integration point for an authorised official registry API.

    Disabled unless ``OFFICIAL_REGISTRY_URL`` and ``OFFICIAL_REGISTRY_KEY`` are
    both set by the operator. When disabled it reports ``connected=False`` with a
    clear reason, and returns no results rather than inventing any.
    """

    name = "official"
    source_type = RegistrySourceType.official.value

    def info(self) -> ProviderInfo:
        configured = bool(settings.official_registry_url and settings.official_registry_key)
        if not configured:
            return ProviderInfo(
                name=self.name,
                requested="official",
                connected=False,
                reason=(
                    "Aucune API officielle autorisée n'est configurée. "
                    "Renseigner OFFICIAL_REGISTRY_URL et OFFICIAL_REGISTRY_KEY "
                    "après autorisation de l'autorité compétente."
                ),
                source_type=self.source_type,
            )
        return ProviderInfo(
            name=self.name,
            requested="official",
            connected=True,
            reason="API officielle autorisée configurée.",
            source_type=self.source_type,
        )

    def search(self, query, *, region=None, district=None, facility_type=None, limit=20):
        # No scraping and no invented data: without a verified contract with the
        # authority this returns nothing.
        return []

    def fetch_by_official_id(self, official_id: str) -> FacilityRecord | None:
        return None


class PartnerRegistryProvider(HealthRegistryProvider):
    """Integration point for a facility or network that shares its own list."""

    name = "partner"
    source_type = RegistrySourceType.partner.value

    def info(self) -> ProviderInfo:
        configured = bool(settings.partner_registry_url and settings.partner_registry_key)
        if not configured:
            return ProviderInfo(
                name=self.name,
                requested="partner",
                connected=False,
                reason=(
                    "Aucun flux partenaire configuré. Renseigner "
                    "PARTNER_REGISTRY_URL et PARTNER_REGISTRY_KEY lorsqu'une "
                    "structure partenaire fournit officiellement sa liste."
                ),
                source_type=self.source_type,
            )
        return ProviderInfo(
            name=self.name,
            requested="partner",
            connected=True,
            reason="Flux partenaire configuré.",
            source_type=self.source_type,
        )

    def search(self, query, *, region=None, district=None, facility_type=None, limit=20):
        return []

    def fetch_by_official_id(self, official_id: str) -> FacilityRecord | None:
        return None


def registry_provider_status() -> dict[str, ProviderInfo]:
    """Status of every registry provider, for the honesty endpoint."""
    return {
        "local": LocalRegistryProvider(db=None).info(),
        "official": OfficialRegistryProvider().info(),
        "partner": PartnerRegistryProvider().info(),
    }
