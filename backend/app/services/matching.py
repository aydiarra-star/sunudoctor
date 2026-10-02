"""Facility and professional matching engine.

Matching is deliberately conservative. A high similarity score is useful
information for a human reviewer, but it NEVER produces a definitive validation
on its own. The engine returns a classification and a score; only an audited
human decision (or an explicit official-source confirmation) can raise a
professional's verification level.

The matching is tolerant to accents, case and punctuation so that a user typing
"centre hospitalier de dakar" still finds "Centre Hospitalier de Dakar", while
never silently merging two different facilities.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

# Matching outcomes.
EXACT = "EXACT"
PARTIAL = "PARTIAL"
NONE = "NONE"

# Facility-name tokens that carry little discriminating power on their own.
_GENERIC_TOKENS = {
    "de",
    "du",
    "des",
    "la",
    "le",
    "les",
    "l",
    "d",
    "et",
    "centre",
    "hopital",
    "hospital",
    "poste",
    "sante",
    "health",
    "clinique",
    "clinic",
    "case",
    "caisse",
}


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def normalize_text(text: str | None) -> str:
    """Lowercase, accent-fold and collapse non-alphanumeric characters."""
    if not text:
        return ""
    folded = strip_accents(text).lower()
    return " ".join("".join(c if c.isalnum() else " " for c in folded).split())


def _tokens(text: str) -> list[str]:
    return normalize_text(text).split()


def token_overlap(a: str, b: str) -> float:
    """Jaccard-like overlap on significant tokens (0.0 to 1.0)."""
    ta = {t for t in _tokens(a) if t not in _GENERIC_TOKENS}
    tb = {t for t in _tokens(b) if t not in _GENERIC_TOKENS}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def similarity(a: str, b: str) -> float:
    """Combined similarity score in [0, 1]."""
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    max_len = max(len(na), len(nb))
    edit = 1.0 - levenshtein(na, nb) / max_len
    return round(0.5 * edit + 0.5 * token_overlap(na, nb), 4)


@dataclass
class FacilityMatch:
    facility_id: str
    name: str
    score: float
    outcome: str
    region: str | None = None
    district: str | None = None
    type: str | None = None
    status: str | None = None
    official_id: str | None = None

    @property
    def is_definitive(self) -> bool:
        """A match is never definitive on its own. Kept for explicitness."""
        return False


@dataclass
class ProfessionalMatchResult:
    outcome: str
    score: float
    reasons: list[str]
    requires_human_review: bool
    definitive: bool = False

    def to_dict(self) -> dict:
        return {
            "outcome": self.outcome,
            "score": self.score,
            "reasons": self.reasons,
            "requires_human_review": self.requires_human_review,
            "definitive": self.definitive,
        }


def match_facilities(
    facilities,
    query: str,
    *,
    threshold: float = 0.55,
) -> list[FacilityMatch]:
    """Rank candidate facilities for a free-text query.

    ``facilities`` is an iterable of HealthcareFacility rows. The result is
    ordered by descending score and filtered to plausible candidates.
    """
    matches: list[FacilityMatch] = []
    for facility in facilities:
        score = max(
            similarity(query, facility.name),
            similarity(query, facility.short_name) if facility.short_name else 0.0,
        )
        if score < threshold:
            continue
        outcome = EXACT if score >= 0.98 else PARTIAL
        matches.append(
            FacilityMatch(
                facility_id=facility.id,
                name=facility.name,
                score=score,
                outcome=outcome,
                region=facility.region,
                district=facility.district,
                type=facility.type.value if facility.type else None,
                status=facility.status.value if facility.status else None,
                official_id=facility.official_id,
            )
        )
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches


def match_professional(
    *,
    license_number: str | None,
    full_name: str,
    profession: str | None,
    specialty: str | None,
    official_license: str | None,
    official_name: str | None,
    official_profession: str | None,
    source_available: bool,
) -> ProfessionalMatchResult:
    """Compare submitted professional data against a single source record.

    Returns a classification that a human must confirm. Even an exact license
    match is not ``definitive`` unless the caller explicitly trusts the source.
    """
    reasons: list[str] = []

    if not source_available:
        return ProfessionalMatchResult(
            outcome="SOURCE_UNAVAILABLE",
            score=0.0,
            reasons=[
                "Aucune source officielle autorisée n'est disponible.",
                "Vérification supplémentaire nécessaire.",
            ],
            requires_human_review=True,
        )

    submitted_license = normalize_text(license_number)
    source_license = normalize_text(official_license)

    if submitted_license and source_license and submitted_license == source_license:
        name_score = similarity(full_name, official_name or "")
        reasons.append("Numéro professionnel identique dans la source consultée.")
        if name_score >= 0.9:
            reasons.append("Nom concordant.")
            return ProfessionalMatchResult(
                outcome=EXACT,
                score=round(0.7 + 0.3 * name_score, 4),
                reasons=reasons,
                requires_human_review=True,
            )
        reasons.append("Le nom diffère du nom associé à ce numéro.")
        return ProfessionalMatchResult(
            outcome=PARTIAL,
            score=round(0.5 + 0.3 * name_score, 4),
            reasons=reasons,
            requires_human_review=True,
        )

    if submitted_license and source_license and submitted_license != source_license:
        reasons.append("Numéro professionnel différent de celui de la source.")
        return ProfessionalMatchResult(
            outcome=NONE,
            score=0.0,
            reasons=reasons,
            requires_human_review=True,
        )

    name_score = similarity(full_name, official_name or "")
    if (
        name_score >= 0.9
        and profession
        and official_profession
        and normalize_text(profession) == normalize_text(official_profession)
    ):
        reasons.append("Nom et profession concordants (sans numéro professionnel).")
        return ProfessionalMatchResult(
            outcome=PARTIAL,
            score=round(0.6 * name_score, 4),
            reasons=reasons,
            requires_human_review=True,
        )

    if (
        specialty
        and official_profession
        and normalize_text(specialty) == normalize_text(official_profession)
    ):
        reasons.append("Spécialité concordante mais identité non confirmée.")

    return ProfessionalMatchResult(
        outcome=NONE,
        score=round(0.3 * name_score, 4),
        reasons=reasons or ["Aucune correspondance suffisante."],
        requires_human_review=True,
    )
