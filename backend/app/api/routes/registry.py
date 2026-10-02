"""Health facility referential endpoints.

These endpoints let a user find their facility in the referential. The
referential itself is never invented: it contains only imported records or
explicit, unverified user requests. Region and district selectors expose what
SunuDoctor actually holds; when a district list is empty it is empty, never
filled with made-up names.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_meta, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import (
    FacilityStatus,
    FacilityType,
    HealthcareFacility,
    Professional,
    RegistrySourceType,
    User,
)
from app.schemas import FacilityRequestCreate
from app.services import audit
from app.services.matching import match_facilities, normalize_text
from app.services.registry import registry_provider_status

router = APIRouter(prefix="/registry", tags=["registry"])

# Public administrative regions of Senegal. This is public administrative
# information, not health data, and is offered as a convenience; the district
# list is always derived from the referential and never hardcoded.
REGIONS = [
    "Dakar",
    "Diourbel",
    "Fatick",
    "Kaffrine",
    "Kaolack",
    "Kédougou",
    "Kolda",
    "Louga",
    "Matam",
    "Saint-Louis",
    "Sédhiou",
    "Tambacounda",
    "Thiès",
    "Ziguinchor",
]

FACILITY_TYPE_LABELS = {
    "HOSPITAL": "Hôpital",
    "EPS": "Établissement public de santé",
    "HEALTH_CENTER": "Centre de santé",
    "HEALTH_POST": "Poste de santé",
    "HEALTH_HUT": "Case de santé",
    "CLINIC": "Clinique",
    "MEDICAL_PRACTICE": "Cabinet médical",
    "PARAMEDICAL_PRACTICE": "Cabinet paramédical",
    "LABORATORY": "Laboratoire",
    "IMAGING_CENTER": "Centre d'imagerie",
    "COMMUNITY_HEALTH_STRUCTURE": "Structure communautaire",
    "SPECIALIZED_FACILITY": "Structure spécialisée",
    "MILITARY_FACILITY": "Structure militaire",
    "PARAMILITARY_FACILITY": "Structure paramilitaire",
    "OTHER": "Autre",
}

STATUS_LABELS = {
    "OFFICIAL_VERIFIED": "Source officielle",
    "PARTNER_VERIFIED": "Source partenaire",
    "PENDING_VERIFICATION": "Vérification en attente",
    "UNVERIFIED": "Non vérifiée",
    "INACTIVE": "Inactive",
    "ARCHIVED": "Archivée",
}


def _facility_type(value: str | None) -> FacilityType:
    if not value:
        return FacilityType.other
    try:
        return FacilityType(value.strip().upper())
    except ValueError:
        return FacilityType.other


def _facility_out(facility: HealthcareFacility) -> dict:
    return {
        "id": facility.id,
        "name": facility.name,
        "short_name": facility.short_name,
        "type": facility.type.value,
        "type_label": FACILITY_TYPE_LABELS.get(facility.type.value, facility.type.value),
        "region": facility.region,
        "district": facility.district,
        "commune": facility.commune,
        "address": facility.address,
        "official_id": facility.official_id,
        "source": facility.source,
        "source_type": facility.source_type.value,
        "status": facility.status.value,
        "status_label": STATUS_LABELS.get(facility.status.value, facility.status.value),
        "is_demo": facility.is_demo,
    }


@router.get("/regions")
def list_regions():
    return {"regions": REGIONS}


@router.get("/districts")
def list_districts(region: str | None = None, db: Session = Depends(get_db)):
    """Districts actually present in the referential for a region.

    Never returns invented districts: an empty list means the referential holds
    no facility for that region yet.
    """
    q = db.query(HealthcareFacility.district).filter(
        HealthcareFacility.district.isnot(None),
        HealthcareFacility.status != FacilityStatus.archived,
    )
    if region:
        q = q.filter(HealthcareFacility.region == region)
    districts = sorted({d for (d,) in q.all() if d})
    return {"region": region, "districts": districts}


@router.get("/facility-types")
def list_facility_types():
    return {
        "types": [
            {"value": t.value, "label": FACILITY_TYPE_LABELS.get(t.value, t.value)}
            for t in FacilityType
        ]
    }


@router.get("/providers")
def list_providers():
    """Honest status of every registry provider (nothing is claimed as live)."""
    status_map = registry_provider_status()
    return {
        provider: {
            "requested": info.requested,
            "connected": info.connected,
            "reason": info.reason,
            "source_type": info.source_type,
        }
        for provider, info in status_map.items()
    }


@router.get("/facilities")
def search_facilities(
    q: str | None = Query(default=None),
    region: str | None = None,
    district: str | None = None,
    type: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Search the referential. Tolerant to accents, case and word order."""
    query = db.query(HealthcareFacility).filter(
        HealthcareFacility.status != FacilityStatus.archived
    )
    if region:
        query = query.filter(HealthcareFacility.region == region)
    if district:
        query = query.filter(HealthcareFacility.district == district)
    if type:
        query = query.filter(HealthcareFacility.type == type)

    rows = query.all()
    if not q:
        rows.sort(key=lambda f: f.name)
        return {"results": [_facility_out(f) for f in rows[: max(1, min(limit, 50))]]}

    matches = match_facilities(rows, q, threshold=settings.facility_match_threshold)
    by_id = {f.id: f for f in rows}
    results = []
    for match in matches[: max(1, min(limit, 50))]:
        item = _facility_out(by_id[match.facility_id])
        item["match_score"] = match.score
        item["match_outcome"] = match.outcome
        results.append(item)
    return {"results": results, "query": q}


@router.post("/facilities/request", status_code=201)
def request_facility(
    payload: FacilityRequestCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    """Report a facility missing from the referential.

    Creates a PENDING_VERIFICATION record with source_type=MANUAL. It is never
    marked official and never auto-validated.
    """
    needle = normalize_text(payload.name)
    duplicates = [
        f
        for f in db.query(HealthcareFacility).all()
        if normalize_text(f.name) == needle
        and normalize_text(f.district) == normalize_text(payload.district)
    ]
    if duplicates:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Une structure portant ce nom existe déjà dans le référentiel pour ce district.",
        )

    facility = HealthcareFacility(
        name=payload.name,
        type=_facility_type(payload.type),
        region=payload.region,
        district=payload.district,
        commune=payload.commune,
        address=payload.address,
        phone=payload.phone,
        source=f"Demande utilisateur ({user.email})",
        source_type=RegistrySourceType.manual,
        status=FacilityStatus.pending_verification,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    audit.log_action(
        db,
        action=audit.AuditAction.FACILITY_REQUEST,
        actor=user,
        resource_type="healthcare_facility",
        resource_id=facility.id,
        meta={"name": facility.name, "district": facility.district},
        ip=meta.get("ip"),
    )
    out = _facility_out(facility)
    out["notice"] = (
        "Structure enregistrée comme non vérifiée. Elle devra être confirmée "
        "par une source autorisée avant d'être considérée comme officielle."
    )
    return out


@router.get("/facilities/{facility_id}")
def get_facility(facility_id: str, db: Session = Depends(get_db)):
    facility = db.get(HealthcareFacility, facility_id)
    if facility is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Structure introuvable")
    return _facility_out(facility)


@router.get("/me/facility")
def my_facility(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The professional's current approved affiliation, if any."""
    from app.models.entities import AffiliationStatus, ProfessionalAffiliation

    prof = db.query(Professional).filter(Professional.user_id == user.id).first()
    if prof is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucun profil professionnel")
    affiliation = (
        db.query(ProfessionalAffiliation)
        .filter(
            ProfessionalAffiliation.professional_id == prof.id,
            ProfessionalAffiliation.status == AffiliationStatus.approved,
        )
        .first()
    )
    if affiliation is None:
        return {
            "facility": None,
            "verification_level": prof.verification_level.value,
            "notice": "Aucune appartenance confirmée.",
        }
    facility = db.get(HealthcareFacility, affiliation.facility_id)
    return {
        "facility": _facility_out(facility) if facility else None,
        "affiliation_status": affiliation.status.value,
        "verification_level": prof.verification_level.value,
    }
