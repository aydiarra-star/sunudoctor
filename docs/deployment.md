# Déploiement — SunuDoctor

## Environnements

| Environnement | Usage |
| --- | --- |
| `development` | local, SQLite, mode démo |
| `staging` | pré-production, PostgreSQL |
| `production` | production, PostgreSQL, HTTPS |

Sélection via `ENVIRONMENT`. Aucun secret n'est versionné.

## Frontend — GitHub Pages

Le frontend est une application statique : il se déploie sur GitHub Pages.

1. Le workflow `.github/workflows/ci.yml` construit le frontend et publie
   `frontend/dist` sur GitHub Pages.
2. `VITE_BASE` est défini sur `/<repo>/` pour que les ressources soient résolues
   sous l'URL de projet GitHub Pages.
3. `VITE_API_BASE` doit pointer vers l'URL publique du backend.

### Important : le backend n'est pas sur GitHub Pages

GitHub Pages ne sert que des fichiers statiques. Il ne peut pas héberger l'API
FastAPI persistante. Il faut donc :

```
Frontend  → GitHub Pages
Backend   → hébergement adapté (Render, Railway, Fly.io, VPS…)
Database  → PostgreSQL managé
```

Sans backend connecté, l'interface affiche honnêtement « Backend non connecté »
et n'invente aucune donnée.

## Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Variables requises en production : `SECRET_KEY`, `DATABASE_URL`,
`ENVIRONMENT=production`, et les clés de paiement/IA si les services
correspondants sont activés.

## CI/CD

Pipeline GitHub Actions :

```
Install → Lint → Typecheck → Unit → Integration → E2E → Build → Security → Deploy
```

Le déploiement n'est déclenché que si le build réussit.

## Vérification post-déploiement

1. Ouvrir l'URL publique (attendu : HTTP 200).
2. Vérifier la page d'accueil, le CSS, le JS et les assets.
3. Tester la navigation et le responsive (mobile / tablette / desktop).
4. Vérifier l'absence d'erreur critique dans la console.

## Déploiement en un seul domaine (recommandé pour la démo publique)

L'API FastAPI peut servir le frontend construit, ce qui donne un produit complet
sur une seule URL :

```bash
cd frontend
VITE_BASE=/ VITE_API_BASE=/api npm run build

cd ../backend
FRONTEND_DIST=/chemin/vers/frontend/dist \
SECRET_KEY=<secret-long-et-aléatoire> \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Les routes `/api/*` restent prioritaires (déclarées avant le SPA).
- Toute autre route renvoie `index.html` (routage côté client).
- `FRONTEND_DIST` vide = API seule.

## État réel du déploiement public

| Élément | État |
| --- | --- |
| Instance de démonstration publique | **déployée** (voir README / rapport final) |
| Frontend GitHub Pages | workflow prêt, **nécessite un jeton avec droit `push`** |
| Backend hébergé | **non connecté** (hébergement à provisionner) |
| Base PostgreSQL managée | **non connectée** |

⚠️ Un jeton GitHub en lecture seule ne peut pas pousser : ne jamais prétendre
que le déploiement GitHub Pages a réussi sans vérifier l'URL réellement obtenue.

