"""Health facility registry providers.

The referential of health facilities must come from an authorised source. This
package defines the integration surface for such sources without ever assuming
one exists: when no official API is configured, the provider reports itself as
not connected and no scraping or workaround is attempted.

Provider hierarchy:

    HealthRegistryProvider
        +-- OfficialRegistryProvider   (needs an authorised API; not connected by default)
        +-- PartnerRegistryProvider    (needs a partner feed; not connected by default)
        +-- LocalRegistryProvider      (the referential actually stored in SunuDoctor)
"""
from app.services.registry.base import (
    FacilityRecord,
    HealthRegistryProvider,
    ProviderInfo,
)
from app.services.registry.providers import (
    LocalRegistryProvider,
    OfficialRegistryProvider,
    PartnerRegistryProvider,
    registry_provider_status,
)

__all__ = [
    "FacilityRecord",
    "HealthRegistryProvider",
    "LocalRegistryProvider",
    "OfficialRegistryProvider",
    "PartnerRegistryProvider",
    "ProviderInfo",
    "registry_provider_status",
]
