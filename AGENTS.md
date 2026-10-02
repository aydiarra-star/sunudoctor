# AGENTS.md — SunuDoctor

Persistent notes for agents working in this repository.

## What this is

SunuDoctor is a clinical documentation platform for Senegal: a multilingual
(Wolof + French) AI clinical scribe with patient records, teleconsultation,
coordination and billing. The core loop is
`PARLER → TRANSCRIRE → STRUCTURER → VÉRIFIER → VALIDER`.

**Non-negotiable product rule: ZERO INVENTED CLINICAL DATA.** The AI must never
invent a diagnosis, symptom, medication, dose, allergy, result or identity. When
information is absent it is "Non documenté"; when uncertain it is "À vérifier".
A generated note is always a `draft_ai` until a professional validates it.

## Layout

| Path | Contents |
| --- | --- |
| `backend/` | FastAPI + SQLAlchemy + Alembic. Tests in `backend/tests`. |
| `frontend/` | React + Vite + TypeScript SPA. Tests via Vitest. |
| `load/` | Locust load test. |
| `docs/` | Architecture, security, AI, wolof-ai, telemedicine, offline, database, deployment, testing, privacy. |
| `deploy/gh-pages/` | Notes for the static GitHub Pages deployment. |

## Commands

```bash
# Backend
cd backend
python -m ruff check app tests
python -m pytest -q                     # 175 tests
python -m alembic upgrade head          # migrations (dev/test use create_all)

# Frontend
cd frontend
npm run lint && npm run typecheck && npm test
npm run build                           # VITE_BASE=/<repo>/ for Pages

# Full production stack
cp .env.production.example .env.production
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

## Conventions and gotchas

- **bcrypt is used directly** (`app/core/security.py`). Do not reintroduce
  passlib: passlib 1.7.4 probes `bcrypt.__about__`, which bcrypt 4.x removed,
  and logs a traceback on first hash.
- **`app/models/__init__.py` must import every entity.** Alembic autogenerate
  depends on it; an empty file silently produces empty migrations.
- **Production fails fast.** `Settings.production_problems()` runs at startup and
  raises when `ENVIRONMENT=production` with an unsafe config (default secret,
  SQLite, a "live" provider without keys, `PAYMENT_MODE=live` without a webhook
  secret). Keep demo and live strictly separated.
- **Honesty over appearance.** Capability endpoints (`/api/meta`) report
  `connected: false` unless a provider is both selected *and* credentialed.
  Never display "connecté / vérifié / payé" for a service that is not really on.
- **Clinical and billing data never mix.** A failed payment must never touch a
  clinical record.

## Known limits

- Public GitHub Pages serves the frontend only. The persistent backend needs
  separate hosting (Render, Railway, Fly.io, VPS) with PostgreSQL.
- Live AI (Azure Speech / OpenAI), real payment providers (Wave, Orange Money),
  and TURN for WebRTC all require credentials and are `NON CONNECTÉ` until set.
- Pushing to GitHub requires a token with `push` scope; the sandbox token is
  read-only.
- **GitHub Actions only scans `.github/workflows/`.** The CI file currently
  lives at `.github/ci.yml`, which GitHub never executes. Moving it requires a
  token with the `workflow` scope; the `repo`-scoped PAT gets
  `refusing to allow a Personal Access Token to create or update workflow`.
- The `gh-pages` branch is deployed manually (`npm run build` with
  `VITE_BASE=/sunudoctor/`, then commit `frontend/dist` to `gh-pages`). This
  path only needs `repo` scope and works even without the `workflow` scope.

## Verification module (LOT 3)

- Verification never auto-validates. A no-match yields "additional verification
  required", never a fraud accusation.
- Badges come from `app/services/verification.py::badge`; they never mention the
  Ministry of Health unless an authorised source actually confirmed.
- The facility registry is **not fabricated**: the local referential is empty
  until controlled imports run. Regions are public administrative data;
  districts are derived and may legitimately be empty.
- Registration for professionals requires a facility block (`facility_id` or
  `requested_facility_name`).
- `require_verified_professional` gates clinical scribe writes.
