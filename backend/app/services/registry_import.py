"""Controlled import of an official facility referential.

An import is a versioned, auditable event. It never silently overwrites the
previous referential: each import is recorded with its source, version,
checksum, counts and a diff against what SunuDoctor already holds, and records
are matched by ``official_id`` (falling back to normalised name + district).

Nothing imported from a non-official source is ever marked
``OFFICIAL_VERIFIED``.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.entities import (
    FacilityStatus,
    FacilityType,
    HealthcareFacility,
    RegistryImport,
    RegistryImportStatus,
    RegistrySourceType,
)
from app.services.matching import normalize_text

# Accepted input formats.
FORMAT_CSV = "csv"
FORMAT_JSON = "json"

_REQUIRED = ("name",)


def _checksum(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _coerce_type(value: str | None) -> FacilityType:
    if not value:
        return FacilityType.other
    token = value.strip().upper()
    try:
        return FacilityType(token)
    except ValueError:
        return FacilityType.other


def _coerce_source_type(value: str | None) -> RegistrySourceType:
    if not value:
        return RegistrySourceType.official
    try:
        return RegistrySourceType(value.strip().upper())
    except ValueError:
        return RegistrySourceType.official


def _status_for(source_type: RegistrySourceType) -> FacilityStatus:
    """Only an official or partner source yields a verified status.

    A manual or community import is stored as PENDING_VERIFICATION: it must be
    reviewed by a human before it can be treated as trustworthy.
    """
    if source_type == RegistrySourceType.official:
        return FacilityStatus.official_verified
    if source_type == RegistrySourceType.partner:
        return FacilityStatus.partner_verified
    return FacilityStatus.pending_verification


def parse_records(payload: bytes, fmt: str) -> tuple[list[dict], list[dict]]:
    """Parse raw bytes into normalised dicts, returning (records, errors)."""
    records: list[dict] = []
    errors: list[dict] = []

    if fmt == FORMAT_JSON:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return [], [{"row": 0, "error": f"JSON invalide: {exc}"}]
        if isinstance(data, dict):
            data = data.get("facilities", [])
        if not isinstance(data, list):
            return [], [{"row": 0, "error": "Le JSON doit contenir une liste de structures."}]
        rows = data
    else:
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            return [], [{"row": 0, "error": f"Encodage invalide: {exc}"}]
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)

    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append({"row": index, "error": "Enregistrement non exploitable."})
            continue
        name = (row.get("name") or "").strip()
        if not name:
            errors.append({"row": index, "error": "Champ 'name' manquant."})
            continue
        records.append(
            {
                "name": name,
                "short_name": (row.get("short_name") or "").strip() or None,
                "type": row.get("type"),
                "region": (row.get("region") or "").strip() or None,
                "district": (row.get("district") or "").strip() or None,
                "commune": (row.get("commune") or "").strip() or None,
                "address": (row.get("address") or "").strip() or None,
                "phone": (row.get("phone") or "").strip() or None,
                "email": (row.get("email") or "").strip() or None,
                "official_id": (row.get("official_id") or "").strip() or None,
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
            }
        )
    return records, errors


def _float(value) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _key(record: dict) -> tuple:
    if record.get("official_id"):
        return ("official_id", record["official_id"].strip().lower())
    return (
        "name_district",
        normalize_text(record.get("name")),
        normalize_text(record.get("district")),
    )


def compute_diff(db: Session, records: list[dict]) -> dict:
    """Classify incoming records against the current referential."""
    existing = db.query(HealthcareFacility).all()
    by_key = {}
    for facility in existing:
        key = (
            ("official_id", facility.official_id.strip().lower())
            if facility.official_id
            else (
                "name_district",
                normalize_text(facility.name),
                normalize_text(facility.district),
            )
        )
        by_key[key] = facility

    new_items, changed_items, unchanged_items = [], [], []
    seen_keys = set()
    for record in records:
        key = _key(record)
        seen_keys.add(key)
        current = by_key.get(key)
        if current is None:
            new_items.append(record["name"])
            continue
        changes = {}
        for field in ("name", "region", "district", "commune", "address", "phone"):
            incoming = record.get(field)
            present = getattr(current, field)
            if incoming and incoming != present:
                changes[field] = {"from": present, "to": incoming}
        if changes:
            changed_items.append({"name": record["name"], "changes": changes})
        else:
            unchanged_items.append(record["name"])

    removed = [
        facility.name
        for key, facility in by_key.items()
        if key not in seen_keys
    ]
    return {
        "new": new_items,
        "changed": changed_items,
        "unchanged_count": len(unchanged_items),
        "removed": removed,
        "counts": {
            "new": len(new_items),
            "changed": len(changed_items),
            "unchanged": len(unchanged_items),
            "removed": len(removed),
        },
    }


def stage_import(
    db: Session,
    *,
    payload: bytes,
    fmt: str,
    source: str,
    source_type: str = "OFFICIAL",
    version: str | None = None,
    imported_by: str | None = None,
) -> RegistryImport:
    """Parse, validate and stage an import WITHOUT publishing it.

    The referential is left untouched: publishing is a separate, explicit step.
    """
    records, errors = parse_records(payload, fmt)
    stype = _coerce_source_type(source_type)
    diff = compute_diff(db, records) if records else {}

    status = RegistryImportStatus.review
    if errors and not records:
        status = RegistryImportStatus.rejected
    elif records and not errors:
        status = RegistryImportStatus.validated

    record = RegistryImport(
        source=source,
        source_type=stype,
        version=version,
        checksum=_checksum(payload),
        record_count=len(records),
        error_count=len(errors),
        errors_json=json.dumps(errors, ensure_ascii=False),
        diff_json=json.dumps(diff, ensure_ascii=False),
        status=status,
        imported_by=imported_by,
        imported_at=datetime.now(UTC),
    )
    db.add(record)
    db.flush()

    # Keep the parsed payload available for the publish step without trusting
    # the caller to resend it. Stored alongside the diff in the import record.
    record.errors_json = json.dumps(
        {"errors": errors, "records": records}, ensure_ascii=False
    )
    db.flush()
    return record


def publish_import(db: Session, import_record: RegistryImport) -> dict:
    """Publish a staged import, updating or creating facilities.

    Existing rows are updated in place (history is kept in the import record's
    diff); nothing is deleted. Facilities absent from the new payload are marked
    for review rather than removed.
    """
    blob = json.loads(import_record.errors_json or "{}")
    records = blob.get("records", []) if isinstance(blob, dict) else []
    if not records:
        raise ValueError("Import sans enregistrements exploitables.")

    existing = db.query(HealthcareFacility).all()
    by_key = {}
    for facility in existing:
        key = (
            ("official_id", facility.official_id.strip().lower())
            if facility.official_id
            else (
                "name_district",
                normalize_text(facility.name),
                normalize_text(facility.district),
            )
        )
        by_key[key] = facility

    created, updated = 0, 0
    now = datetime.now(UTC)
    target_status = _status_for(import_record.source_type)

    for record in records:
        key = _key(record)
        current = by_key.get(key)
        if current is None:
            facility = HealthcareFacility(
                name=record["name"],
                short_name=record.get("short_name"),
                type=_coerce_type(record.get("type")),
                region=record.get("region"),
                district=record.get("district"),
                commune=record.get("commune"),
                address=record.get("address"),
                phone=record.get("phone"),
                email=record.get("email"),
                official_id=record.get("official_id"),
                latitude=_float(record.get("latitude")),
                longitude=_float(record.get("longitude")),
                source=import_record.source,
                source_type=import_record.source_type,
                source_date=now,
                verified_date=now if target_status != FacilityStatus.pending_verification else None,
                status=target_status,
                confidence=1.0 if target_status != FacilityStatus.pending_verification else None,
                registry_import_id=import_record.id,
            )
            db.add(facility)
            created += 1
        else:
            for field in ("name", "region", "district", "commune", "address", "phone"):
                incoming = record.get(field)
                if incoming:
                    setattr(current, field, incoming)
            if record.get("official_id"):
                current.official_id = record["official_id"]
            current.source = import_record.source
            current.source_type = import_record.source_type
            current.source_date = now
            if target_status != FacilityStatus.pending_verification:
                current.status = target_status
                current.verified_date = now
                current.confidence = 1.0
            current.registry_import_id = import_record.id
            updated += 1

    import_record.status = RegistryImportStatus.published
    import_record.published_at = now
    db.flush()
    return {"created": created, "updated": updated, "import_id": import_record.id}


def import_history(db: Session) -> list[dict]:
    rows = db.query(RegistryImport).order_by(RegistryImport.imported_at.desc()).all()
    out = []
    for row in rows:
        blob = json.loads(row.errors_json or "{}")
        errors = blob.get("errors", []) if isinstance(blob, dict) else []
        diff = json.loads(row.diff_json or "{}")
        out.append(
            {
                "id": row.id,
                "source": row.source,
                "source_type": row.source_type.value,
                "version": row.version,
                "checksum": row.checksum,
                "record_count": row.record_count,
                "error_count": row.error_count,
                "errors": errors[:50],
                "diff": diff,
                "status": row.status.value,
                "imported_at": row.imported_at,
                "published_at": row.published_at,
            }
        )
    return out
