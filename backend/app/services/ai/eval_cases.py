"""Wolof / French clinical evaluation cases.

Each case documents an input and the invariant the pipeline must preserve.
These are the canonical, human-readable evaluation suite referenced by the
automated tests (see backend/tests/test_wolof_eval.py) and by /docs/wolof-ai.md.

The suite covers: Wolof, French, Wolof/French code-switching, negations, dates,
numbers, medications, symptoms, noise markers and accents.

Limits (documented honestly): with no real Wolof speech-to-text engine
configured, transcription of raw audio is NOT available. The cases below are
evaluated against the structuring/safety stages, which are language-agnostic and
do not invent content.
"""
from __future__ import annotations

CASES: list[dict] = [
    {
        "id": "wo-001",
        "language": "wolof+fr",
        "input": "Patient bi dafa am douleur ci ventre bi depuis trois days, te fièvre du.",
        "invariants": [
            "douleur abdominale conservée",
            "fièvre marquée comme niée (fièvre du = pas de fièvre)",
            "aucune dose inventée",
            "aucun diagnostic généré",
        ],
    },
    {
        "id": "fr-002",
        "language": "fr",
        "input": "Patient sans fièvre, pas de vomissements, douleur à la tête depuis deux jours.",
        "invariants": [
            "fièvre et vomissements ne doivent PAS devenir positifs",
            "douleur à la tête conservée",
        ],
    },
    {
        "id": "wo-003",
        "language": "wolof",
        "input": "Xamuma bu baax, peut-être fièvre am na.",
        "invariants": ["incertitude conservée", "aucune valeur inventée"],
    },
    {
        "id": "med-004",
        "language": "fr",
        "input": "Prescrire paracétamol 5 mg, pas 50 mg.",
        "invariants": [
            "les nombres 5 et 50 doivent être distingués exactement",
            "aucune dose non présente dans la transcription",
        ],
    },
    {
        "id": "med-005",
        "language": "fr",
        "input": "Amoxicilline 0,5 mg puis 5 ml.",
        "invariants": ["séparateur décimal normalisé", "0,5 et 5 non confondus"],
    },
    {
        "id": "neg-006",
        "language": "fr",
        "input": "Pas d'allergie connue. Aucun antécédent.",
        "invariants": ["absence d'allergie conservée comme négation", "aucune allergie inventée"],
    },
    {
        "id": "date-007",
        "language": "wo+fr",
        "input": "Depuis trois days, fièvre am na, met bi dafa metti.",
        "invariants": ["durée conservée", "aucune date absolue inventée"],
    },
    {
        "id": "noise-008",
        "language": "wo",
        "input": "[bruit] ... patient ... xamuma ... [bruit]",
        "invariants": ["incertitude conservée", "aucune donnée inventée à partir du bruit"],
    },
    {
        "id": "acc-009",
        "language": "fr",
        "input": "Fièvre présente, température 38,5.",
        "invariants": ["accents normalisés", "38,5 conservé exactement"],
    },
    {
        "id": "absent-010",
        "language": "fr",
        "input": "Le patient consulte ce jour.",
        "invariants": [
            "aucun symptôme inventé",
            "information absente marquée Non documenté",
        ],
    },
]
