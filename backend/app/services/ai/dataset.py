"""Synthetic, anonymised clinical evaluation dataset.

NOTHING in this file is real patient data. Every name, number and case is
invented for testing the pipeline. The dataset is deliberately small and covers
the situations SunuDoctor must handle correctly:

- Wolof, French, and Wolof/French code-switching
- negations ("pas de fièvre", "fièvre du", "amul")
- uncertainty ("xamuma", "peut-être", "je ne sais pas")
- medications and doses (5 mg vs 50 mg, 0,5 mg, 5 ml)
- dates and durations
- symptoms and history
- noise markers
- accents

Each entry has:
  id            stable identifier
  language      wo | fr | wo+fr
  transcript    the raw text (what STT would produce)
  reference     an expected normalised summary, used only for metrics
  must_not_contain  substrings the pipeline must NEVER emit as positive facts
"""
from __future__ import annotations

DATASET: list[dict] = [
    {
        "id": "syn-wo-001",
        "language": "wo+fr",
        "transcript": (
            "Patient bi dafa am douleur ci ventre bi depuis trois days, te fièvre du."
        ),
        "reference": "douleur ventre depuis trois days",
        "must_not_contain": ["fièvre présente"],
    },
    {
        "id": "syn-fr-002",
        "language": "fr",
        "transcript": (
            "Patient sans fièvre, pas de vomissements, douleur à la tête depuis deux jours."
        ),
        "reference": "douleur tête depuis deux jours",
        "must_not_contain": ["fièvre présente", "vomissements présents"],
    },
    {
        "id": "syn-wo-003",
        "language": "wo",
        "transcript": "Xamuma bu baax, peut-être fièvre am na.",
        "reference": "",
        "must_not_contain": ["fièvre confirmée"],
    },
    {
        "id": "syn-med-004",
        "language": "fr",
        "transcript": "Prescrire paracétamol 5 mg, pas 50 mg.",
        "reference": "paracétamol 5 mg",
        "must_not_contain": ["50 mg"],
    },
    {
        "id": "syn-med-005",
        "language": "fr",
        "transcript": "Amoxicilline 0,5 mg puis 5 ml.",
        "reference": "amoxicilline 0.5 mg 5 ml",
        "must_not_contain": [],
    },
    {
        "id": "syn-neg-006",
        "language": "fr",
        "transcript": "Pas d'allergie connue. Aucun antécédent.",
        "reference": "",
        "must_not_contain": ["allergie présente", "antécédent présent"],
    },
    {
        "id": "syn-date-007",
        "language": "wo+fr",
        "transcript": "Depuis trois days, fièvre am na, met bi dafa metti.",
        "reference": "depuis trois days",
        "must_not_contain": [],
    },
    {
        "id": "syn-noise-008",
        "language": "wo",
        "transcript": "[bruit] ... patient ... xamuma ... [bruit]",
        "reference": "",
        "must_not_contain": ["symptôme confirmé"],
    },
    {
        "id": "syn-acc-009",
        "language": "fr",
        "transcript": "Fièvre présente, température 38,5.",
        "reference": "fièvre présente température 38.5",
        "must_not_contain": [],
    },
    {
        "id": "syn-absent-010",
        "language": "fr",
        "transcript": "Le patient consulte ce jour.",
        "reference": "",
        "must_not_contain": ["fièvre", "douleur", "toux"],
    },
    {
        "id": "syn-multi-011",
        "language": "wo+fr",
        "transcript": (
            "Sama bopp dafa metti, j'ai mal à la tête depuis hier, "
            "xamuma si température bi, pas de toux."
        ),
        "reference": "mal tête depuis hier",
        "must_not_contain": ["toux présente"],
    },
    {
        "id": "syn-dose-012",
        "language": "fr",
        "transcript": "Métformine 500 mg matin et soir, pas 50 mg.",
        "reference": "métformine 500 mg",
        "must_not_contain": ["50 mg"],
    },
]
