# Tests — SunuDoctor

## Résumé

| Suite | Outil | Contenu |
| --- | --- | --- |
| Backend unitaires/intégration | pytest | auth, RBAC, anti-hallucination, Wolof, scribe, facturation |
| Frontend | vitest | file hors ligne, page d'accueil, page de statut |

## Backend (`backend/tests/`)

```bash
cd backend
pytest -q
```

- `test_auth_rbac.py` — inscription, connexion, isolation des patients,
  interdiction d'accès administrateur aux dossiers, break-glass.
- `test_anti_hallucination.py` — ancrage, négation, incertitude, diagnostic
  interdit, doses.
- `test_wolof_eval.py` — suite d'évaluation wolof/français/code-switching.
- `test_scribe_pipeline.py` — chaîne transcrire → structurer → valider + versions.
- `test_billing_and_safety.py` — tarifs, séparation clinique/facturation,
  fournisseurs.

## Frontend (`frontend/src/`)

```bash
cd frontend
npm test
```

## Tests anti-hallucination — cas critiques

| Entrée | Attendu |
| --- | --- |
| « Pas de fièvre » | reste une négation, jamais « Fièvre présente » |
| « Je ne sais pas » | reste incertain, aucune valeur inventée |
| « 5 mg » / « 50 mg » | distingués exactement |
| « 0,5 mg » / « 5 ml » | unités et valeurs distinctes |
| Diagnostic absent | « Non documenté », jamais deviné |

## Tests de permissions

- Un médecin ne voit pas les patients d'un autre sans `care_team_access`.
- Un patient ne voit que son dossier.
- Un administrateur ne lit pas les données cliniques.
- Le break-glass exige raison + durée et est audité.

## Limites

- Pas de tests E2E navigateur (Playwright) encore : à ajouter.
- Les tests d'accessibilité automatiques (axe) restent à intégrer.
- Les tests de charge/performance ne sont pas encore en place.
