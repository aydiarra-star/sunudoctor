# Confidentialité et données — SunuDoctor

## Principes

1. **Zéro invention.** Aucune donnée réelle (patient, professionnel, structure)
   n'est créée par le système.
2. **Minimisation.** Seules les données nécessaires au soin sont collectées.
3. **Traçabilité.** Tout accès à un dossier est journalisé.
4. **Consentement.** Les consentements (accès, partage, téléconsultation, audio,
   IA, recherche) sont explicites et révocables.

## Données de démonstration

Les données synthétiques sont **explicitement marquées** :

- drapeau `is_demo` en base ;
- étiquette « DEMO » dans l'interface ;
- bandeau « Mode démonstration » ;
- `GET /api/meta` expose les capacités en mode `demo`.

Elles ne doivent jamais être présentées comme réelles.

## Séparation clinique / facturation

Les données de facturation sont isolées. Un abonnement impayé ne peut pas
supprimer ni modifier une donnée clinique.

## Séparation administration / clinique

Un administrateur technique gère la plateforme mais n'accède pas aux dossiers
médicaux. Toute exception passe par un accès exceptionnel (break-glass) motivé,
limité dans le temps et audité.

## Conservation

- L'audio original n'est conservé que si le consentement correspondant est
  donné.
- Les versions de notes sont conservées pour la traçabilité clinique.

## Conformité — À VALIDER

⚠️ La conformité réglementaire sénégalaise en matière de données de santé
(autorisations, hébergement, transferts) **nécessite une validation juridique**.
Rien dans cette plateforme ne doit être présenté comme « conforme » avant cette
validation.

## Contact et exercice des droits

Les patients peuvent consulter leurs documents et gérer leurs consentements
depuis leur espace. L'exercice formel des droits (accès, rectification,
suppression) **reste à définir** avec les autorités compétentes.
