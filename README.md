# SunuDoctor

**La santé connectée, au service de tous.**

Un copilote numérique pour documenter, coordonner et faciliter les soins au
Sénégal.

> ⚠️ **Mode démonstration.** Cette instance n'est pas une plateforme de
> production. Les fonctions d'IA utilisent des données synthétiques et aucun
> service externe réel (voix, vidéo, paiement) n'est connecté. Aucune donnée
> médicale réelle n'est hébergée. Voir `docs/` et la page `/status` de
> l'application.

## Le cœur du produit

```
PARLER → TRANSCRIRE → STRUCTURER → VÉRIFIER → VALIDER
```

Une note générée par l'IA reste un **brouillon** tant qu'un professionnel ne l'a
pas validée. L'IA n'invente jamais : information absente = « Non documenté »,
incertitude = « À vérifier ».

## Architecture

Monorepo :

- `backend/` — API **FastAPI** (Python 3.11+), SQLAlchemy 2.0, JWT, RBAC,
  audit, break-glass, IA modulaire, facturation.
- `frontend/` — application **React + TypeScript + Vite** avec un design system
  Tailwind, responsive et accessible.
- `docs/` — documentation complète (architecture, sécurité, IA, Wolof,
  téléconsultation, hors ligne, base de données, déploiement, tests,
  confidentialité).
- `.github/workflows/` — CI/CD GitHub Actions.

## Installation

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env      # valeurs fictives uniquement
uvicorn app.main:app --reload --port 8000
```

API : http://127.0.0.1:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev                  # http://localhost:5173
```

Pour connecter le frontend au backend local :

```bash
VITE_API_BASE=http://127.0.0.1:8000/api npm run dev
```

## Variables d'environnement

Voir `.env.example`. **Aucun secret réel ne doit être versionné.**

| Variable | Rôle |
| --- | --- |
| `SECRET_KEY` | signature des jetons JWT |
| `DATABASE_URL` | connexion base de données |
| `ENVIRONMENT` | `development` / `staging` / `production` |
| `AI_MODE` | `demo` ou `live` |
| `PAYMENT_MODE` | `demo` ou `live` |
| `VITE_API_BASE` | URL publique de l'API (frontend) |

## Tests

```bash
cd backend && pytest -q          # 65 tests
cd frontend && npm test          # 4 tests
```

Voir `docs/testing.md`.

## Documentation

- [Architecture](docs/architecture.md)
- [Sécurité](docs/security.md)
- [IA clinique](docs/ai.md)
- [IA Wolof](docs/wolof-ai.md)
- [Téléconsultation](docs/telemedicine.md)
- [Mode hors ligne](docs/offline.md)
- [Base de données](docs/database.md)
- [Déploiement](docs/deployment.md)
- [Tests](docs/testing.md)
- [Confidentialité](docs/privacy.md)

## Déploiement

Frontend sur **GitHub Pages**, backend sur un hébergement adapté (GitHub Pages ne
peut pas héberger une API persistante). Voir `docs/deployment.md`.

## Limites connues

- Aucun moteur de reconnaissance vocale wolof réel n'est configuré.
- La vidéo de téléconsultation nécessite la configuration de serveurs ICE.
- Les paiements (Wave, Orange Money, carte) sont abstraits mais non connectés.
- Le mode hors ligne est partiel.
- La conformité réglementaire sénégalaise **reste à valider**.

## Licence

Projet de démonstration. Voir le dépôt pour les conditions d'utilisation.
