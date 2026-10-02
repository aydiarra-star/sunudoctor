# Mode hors ligne — SunuDoctor

## Objectif

Permettre l'usage en zone rurale ou à faible connectivité sans perte de données
et sans invention.

## État réel

| Élément | État |
| --- | --- |
| File de synchronisation locale (`localStorage`) | PARTIEL |
| Détection de connectivité (`navigator.onLine`) | RÉEL |
| Reprise automatique après coupure | À FINALISER |
| Gestion des conflits | À FINALISER |
| Chiffrement du stockage local | À FINALISER |

## Implémentation actuelle

`frontend/src/lib/offline.ts` fournit :

- `enqueue()` : met en file une requête qui n'a pas pu être envoyée ;
- `getQueue()` : liste les éléments en attente ;
- `clearQueue()` : vide la file après synchronisation ;
- `isOnline()` : état de connectivité.

Les éléments en attente sont **visibles** et marqués comme non synchronisés.
Aucune donnée n'est présentée comme synchronisée tant qu'elle ne l'est pas
réellement.

## Reste à faire

1. Chiffrer le stockage local (WebCrypto) pour les données de santé.
2. Rejouer automatiquement la file au retour de la connexion.
3. Résoudre les conflits (stratégie « dernière écriture validée par un
   professionnel gagne », avec journal).
4. Mettre en cache les dossiers consultés pour lecture hors ligne.

Ces éléments nécessitent des tests supplémentaires avant d'être déclarés
opérationnels.
