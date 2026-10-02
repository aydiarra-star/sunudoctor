# Vérification des professionnels et référentiel des structures

Ce module réduit le risque de faux professionnels (médecins, infirmiers,
sages-femmes, paramédicaux) et de fausses appartenances à une structure de
santé. Il s'appuie sur un référentiel de structures et sur une vérification
progressive, toujours sous contrôle humain.

Principe directeur : **ne jamais transformer une absence de correspondance en
accusation**. Une personne non retrouvée n'est pas un « faux médecin » : c'est
un dossier qui nécessite une **vérification supplémentaire**.

## Quatre notions distinctes (jamais confondues)

Le système sépare explicitement :

1. une **source officielle disponible** ;
2. une **intégration officielle autorisée** ;
3. une **vérification SunuDoctor** ;
4. une **confirmation d'appartenance par la structure**.

Une source peut exister sans être autorisée ; une intégration peut être
autorisée sans que SunuDoctor ait encore vérifié un dossier ; une structure peut
confirmer une appartenance sans que l'identité professionnelle soit vérifiée au
niveau national.

## Niveaux de vérification

| Niveau | Signification | Portée |
| --- | --- | --- |
| `UNVERIFIED` | Compte créé, aucune vérification | Accès limité |
| `IDENTITY_SUBMITTED` | Pièces déclarées, en attente d'examen | Accès limité |
| `FACILITY_MATCHED` | Correspondance de structure proposée | Accès limité |
| `PROFESSIONAL_PENDING` | Vérification professionnelle en cours | Accès limité |
| `VERIFIED` | Vérifié par un vérificateur SunuDoctor | Documentation clinique |
| `FACILITY_ADMIN_VERIFIED` | Appartenance confirmée par la structure | Documentation clinique |
| `OFFICIAL_SOURCE_VERIFIED` | Confirmé par une source officielle autorisée | Documentation clinique |
| `REJECTED` | Vérification refusée | Aucun accès clinique |
| `SUSPENDED` | Compte suspendu | Aucun accès clinique |
| `DUPLICATE_REVIEW` | Doublon potentiel détecté | Aucun accès clinique |

Le badge affiché provient du backend. Il ne mentionne **jamais** le Ministère de
la Santé ni une validation institutionnelle : SunuDoctor ne prétend pas être
connecté au Ministère sans intégration officiellement autorisée.

## Écrire des soins exige une vérification

Les endpoints d'écriture clinique (`/api/scribe/*`) exigent un professionnel
vérifié (`require_verified_professional`). Un compte non vérifié conserve un
accès limité : il peut préparer son profil et soumettre des pièces, mais pas
documenter des soins. Ce comportement est piloté par
`REQUIRE_VERIFIED_PROFESSIONAL` (activé par défaut).

## Référentiel des structures

`app/services/registry/` expose une abstraction de fournisseurs :

| Fournisseur | Statut par défaut | Remarque |
| --- | --- | --- |
| `official` | NON CONNECTÉ | Aucune API officielle n'est appelée sans autorisation |
| `partner` | NON CONNECTÉ | Intégration partenaire non configurée |
| `local` | CONNECTÉ | Référentiel interne (imports contrôlés + demandes) |

Le référentiel interne contient uniquement des enregistrements **importés** ou
des **demandes** explicitement non vérifiées. Aucune structure n'est inventée :
les listes de districts sont dérivées du référentiel et peuvent être vides.

### Import contrôlé

`app/services/registry_import.py` implémente un import en deux temps :

1. **staging** : source, version, checksum, diff (nouveaux / modifiés / conflits) ;
2. **publication** explicite par un vérificateur.

Rien n'est appliqué silencieusement. Une structure issue d'une source
`COMMUNITY` ou `MANUAL` reste `PENDING_VERIFICATION` et n'est jamais promue
`OFFICIAL_VERIFIED`.

## Correspondance (matching)

`app/services/matching.py` compare noms, licences et structures, avec tolérance
aux accents, à la casse et à l'ordre des mots. Toute correspondance :

- n'est **pas** définitive (`definitive = False`) ;
- exige une **revue humaine** (`requires_human_review = True`) ;
- explique ses raisons.

Lorsqu'aucune source officielle autorisée n'est configurée, le résultat vaut
`SOURCE_UNAVAILABLE` avec le message « Vérification supplémentaire nécessaire ».

## Doublons

La détection de doublons est **informative** : un doublon suspecté est signalé
et routé vers une revue humaine, jamais fusionné ni supprimé automatiquement.

Signaux retenus : même numéro de licence, même e-mail, même téléphone, ou
combinaison **nom + profession + structure**. Une simple similarité de nom
(prénom/nom commun) ne suffit jamais.

## Séparation des tâches

- Un **vérificateur ne peut pas vérifier sa propre identité**.
- Un **administrateur de structure ne peut pas confirmer sa propre
  appartenance**.
- Le niveau `OFFICIAL_SOURCE_VERIFIED` est refusé si aucune source officielle
  autorisée n'est configurée.
- Chaque décision est auditée (`IDENTITY_SUBMIT`, `VERIFICATION_REVIEW`,
  `AFFILIATION_REQUEST`, `AFFILIATION_DECISION`, `REGISTRY_IMPORT`,
  `REGISTRY_PUBLISH`, `FACILITY_REQUEST`).

## Parcours d'inscription professionnelle

```
Profession → Région → Structure (référentiel) → Fonction
→ Identité professionnelle → Documents → Vérification → Accès clinique
```

L'inscription professionnelle **exige** une structure : soit sélectionnée dans
le référentiel (`facility_id`), soit demandée en vérification
(`requested_facility_name`). Dans le second cas, la structure est créée
`PENDING_VERIFICATION`, jamais officielle.

## Configuration

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `REQUIRE_VERIFIED_PROFESSIONAL` | Bloque l'écriture clinique non vérifiée | `true` |
| `OFFICIAL_REGISTRY_URL` | URL d'une source officielle autorisée | vide |
| `OFFICIAL_REGISTRY_KEY` | Clé de la source officielle | vide |
| `FACILITY_MATCH_THRESHOLD` | Seuil de correspondance | interne |

Sans `OFFICIAL_REGISTRY_URL` **et** `OFFICIAL_REGISTRY_KEY`, aucune connexion
officielle n'est revendiquée.

## Tests

`backend/tests/test_verification.py` couvre les scénarios exigés :

1. professionnel trouvé → vérification possible ;
2. professionnel absent → vérification manuelle, jamais « faux médecin » ;
3. structure trouvée → association possible ;
4. structure inexistante → demande de vérification ;
5. identifiant erroné → refus ou vérification supplémentaire ;
6. doublon → revue, jamais fusion/suppression automatique ;
7. document falsifié → refus/suspension ;
8. changement de structure → historique conservé ;
9. auto-vérification → empêchée.

Plus les garanties anti-invention : aucun référentiel fabriqué, aucune
validation automatique, aucune revendication ministérielle.
