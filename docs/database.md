# Base de données — SunuDoctor

## Choix

- **Développement / tests** : SQLite (fichier ou mémoire).
- **Production** : PostgreSQL recommandé (concurrence, extensions, sauvegardes).

Le code utilise SQLAlchemy 2.0 avec un modèle déclaratif typé, portable entre les
deux.

## Schéma

### Identité et organisations

| Table | Rôle |
| --- | --- |
| `users` | comptes (email, mot de passe haché, rôle, MFA) |
| `professionals` | informations professionnelles + statut de vérification |
| `organizations` | structures (cabinet, centre, clinique, hôpital, réseau) |
| `care_team_access` | autorisation ressource : qui peut accéder à quel patient |

### Clinique

| Table | Rôle |
| --- | --- |
| `patients` | identité et coordonnées |
| `encounters` | rencontres cliniques |
| `consultations` | consultations (statut, version, validation) |
| `observations` | constantes et observations |
| `allergies` | allergies |
| `medications` | traitements |
| `documents` | documents versionnés |
| `appointments` | rendez-vous |
| `teleconsultations` | téléconsultations |
| `referrals` | orientations / coordination |
| `consents` | consentements |
| `messages` | messagerie interne |

### IA

| Table | Rôle |
| --- | --- |
| `ai_transcriptions` | transcriptions (brute, corrigée, audio, consentement) |
| `ai_structured_notes` | notes structurées + drapeaux de sécurité |
| `note_versions` | historique des versions d'une note |

### Facturation (séparée du clinique)

| Table | Rôle |
| --- | --- |
| `subscriptions` | abonnements |
| `payments` | paiements |
| `plans` | catalogue de tarifs |

### Sécurité et exploitation

| Table | Rôle |
| --- | --- |
| `audit_logs` | journal d'audit |
| `break_glass_events` | accès exceptionnels |
| `verification_requests` | demandes de vérification professionnelle |
| `notifications` | notifications |

## Règles structurelles

1. **Aucune clé étrangère entre le clinique et la facturation.** Un impayé ne
   peut pas altérer une donnée clinique.
2. Chaque entité porte `is_demo` pour distinguer les données de démonstration.
3. Les suppressions cliniques sont logiques (statut), jamais physiques, afin de
   préserver la traçabilité.

## Migrations

En développement, le schéma est créé automatiquement au démarrage
(`Base.metadata.create_all`). Pour la production, utiliser Alembic (à ajouter
lors du premier déploiement PostgreSQL).
