# Sécurité — SunuDoctor

## Principes

1. Priorité à la sécurité en cas de conflit avec une fonctionnalité.
2. Principe du moindre privilège.
3. Séparation des tâches (administration ≠ accès clinique).
4. Traçabilité de toute action sensible.

## Authentification

- Mots de passe hachés avec bcrypt (jamais stockés en clair).
- Jetons JWT d'accès de courte durée (60 min par défaut) + jeton de
  rafraîchissement (7 jours).
- MFA/TOTP optionnel : `POST /api/auth/mfa/enable` puis
  `POST /api/auth/mfa/confirm`. Le MFA n'est activé qu'après confirmation.
- Limitation de débit par IP sur `/api/auth` et `/api/billing`.

## Autorisation (RBAC)

Le contrôle est **par ressource**, jamais global :

- Un professionnel n'accède qu'aux patients pour lesquels une ligne
  `care_team_access` existe (`view`, `edit`, `full`).
- Un patient n'accède qu'à son propre dossier.
- Un administrateur de plateforme n'a **aucun** accès clinique automatique.
- Toute lecture d'un dossier patient est journalisée (`patient_view`).

## Accès exceptionnel (break-glass)

`POST /api/break-glass` exige une raison détaillée (≥ 10 caractères) et une
durée (≤ 24 h). L'événement est persisté dans `break_glass_events` et
`audit_logs`, et expire automatiquement.

## Audit

`audit_logs` journalise : connexion, consultation de dossier, modification,
export, téléchargement, partage, prescription, validation, changement de
permissions et break-glass. Chaque entrée contient acteur, rôle, ressource,
patient concerné, IP, user-agent, horodatage.

## En-têtes et transport

- HTTPS obligatoire en production (HSTS ajouté automatiquement).
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` restreint la géolocalisation et le micro.

## Validation et injection

- Toute entrée est validée par Pydantic.
- SQLAlchemy paramètre les requêtes (pas de concaténation SQL).
- React échappe le contenu (protection XSS).
- Les uploads sont limités par type et taille à l'entrée.

## Secrets

- Aucun secret dans Git. `.env` est ignoré, `.env.example` ne contient que des
  valeurs fictives.
- Les clés de paiement (Wave, Orange Money, carte) restent côté serveur.
- `GET /api/admin/config` ne renvoie jamais de secret.

## Limites connues

- Le stockage du jeton côté navigateur utilise `localStorage` (à migrer vers un
  cookie httpOnly + SameSite pour un durcissement supplémentaire).
- La limitation de débit est en mémoire (à remplacer par Redis en production
  multi-instances).
- La conformité réglementaire sénégalaise (protection des données de santé)
  **reste à valider** juridiquement.
