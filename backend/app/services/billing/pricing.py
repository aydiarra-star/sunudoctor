"""Launch pricing grid (Tarifs de lancement).

These are the published launch prices requested for the product. They are NOT
the result of an official market study and must be labelled "Tarifs de
lancement" wherever they are displayed.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    code: str
    label: str
    price_fcfa: int
    category: str


PLANS: list[Plan] = [
    Plan("doctor", "Médecin", 15000, "individual"),
    Plan("nurse", "Infirmier", 10000, "individual"),
    Plan("midwife", "Sage-femme", 10000, "individual"),
    Plan("other_professional", "Autre professionnel", 10000, "individual"),
    Plan("community_agent", "Agent communautaire", 5000, "individual"),
    Plan("cabinet", "Cabinet individuel", 20000, "organization"),
    Plan("structure_5", "Structure ≤ 5 utilisateurs", 35000, "organization"),
    Plan("center_10", "Centre ≤ 10 utilisateurs", 50000, "organization"),
    Plan("clinic_20", "Clinique ≤ 20 utilisateurs", 75000, "organization"),
    Plan("clinic_50", "Clinique ≤ 50 utilisateurs", 100000, "organization"),
    Plan("hospital_100", "Hôpital ≤ 100 utilisateurs", 150000, "organization"),
    Plan("network", "Grand réseau", 200000, "organization"),
]

PLANS_BY_CODE = {p.code: p for p in PLANS}

# Role -> default individual plan code.
ROLE_PLAN = {
    "doctor": "doctor",
    "nurse": "nurse",
    "midwife": "midwife",
    "other_professional": "other_professional",
    "community_agent": "community_agent",
    "social_worker": "community_agent",
}


def as_dicts() -> list[dict]:
    return [
        {"code": p.code, "label": p.label, "price_fcfa": p.price_fcfa, "category": p.category}
        for p in PLANS
    ]
