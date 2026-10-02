# Architecture — SunuDoctor

## Vue d'ensemble

SunuDoctor est un monorepo composé de deux applications :

```
sunudoctor/
├── backend/          API FastAPI (Python 3.11+)
│   ├── app/
│   │   ├── core/         config, database, security, rbac
│   │   ├── models/       entités SQLAlchemy
│   │   ├── schemas/      schémas Pydantic
│   │   ├── api/routes/   routes REST
│   │   └── services/     audit, IA, facturation
│   └── tests/            pytest
├── frontend/         Application React + TypeScript (Vite)
│   └── src/
│       ├── lib/          client API, auth, offline
│       ├── components/   design system, layout
│       └── pages/        écrans par rôle
├── docs/             documentation
└── .github/workflows/ CI/CD
```

## Choix techniques

| Domaine | Choix | Justification |
| --- | --- | --- |
| Backend | FastAPI | Typage, validation Pydantic, OpenAPI automatique |
| ORM | SQLAlchemy 2.0 | Modèle déclaratif typé, portabilité SQLite/PostgreSQL |
| Auth | JWT (access + refresh) | Sans état, adapté aux déploiements distribués |
| Frontend | React + TypeScript + Vite | Rapide, typé, écosystème mature |
| Styles | Tailwind CSS | Cohérence, responsive mobile-first |
| Tests | pytest + vitest | Standards des écosystèmes |

## Principe de séparation

L'architecture impose trois séparations strictes :

1. **Données cliniques vs données de facturation.** Un abonnement impayé ne
   supprime ni ne modifie jamais un dossier clinique. Les tables
   `subscriptions`/`payments` sont distinctes de `encounters`/`consultations`.
2. **Administration technique vs accès clinique.** Un administrateur
   (`platform_admin`) gère utilisateurs, structures et audit, mais n'obtient
   aucun accès automatique aux données médicales (voir `app/core/rbac.py`).
3. **Contenu réel vs contenu de démonstration.** Chaque entité porte un drapeau
   `is_demo`. Les capacités synthétiques sont exposées via `/api/meta` et
   affichées comme « Mode démonstration ».

## Flux du Scribe clinique

```
PARLER → TRANSCRIRE → STRUCTURER → VÉRIFIER → VALIDER
  │          │            │           │          │
audio     texte brut   champs      garde-fous  validation
                        structurés  anti-       humaine
                                    hallucination
```

Chaque étape produit une trace persistée (`ai_transcriptions`,
`ai_structured_notes`, `note_versions`) et une entrée d'audit.

## Modularité IA

Quatre interfaces abstraites permettent de remplacer un fournisseur sans
toucher au reste de l'application :

- `SpeechToTextProvider`
- `ClinicalAIProvider`
- `TranslationProvider`
- `SafetyProvider`

La fabrique (`services/ai/factory.py`) retourne le fournisseur configuré et
signale tout repli vers le mode démonstration.

## Environnements

`development` · `staging` · `production`, sélectionnés par `ENVIRONMENT`.
Aucun secret n'est versionné : voir `.env.example`.
