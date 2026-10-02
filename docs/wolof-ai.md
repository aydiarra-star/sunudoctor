# IA Wolof / Français — SunuDoctor

## Exigence

Le moteur doit gérer : **Wolof**, **Français**, et **Wolof + Français** dans une
même phrase (code-switching), et permettre l'ajout futur d'autres langues
nationales.

## Code-switching

L'architecture traite la langue au niveau de la clause, pas de la phrase. Une
consultation peut alterner librement :

> « Patient bi dafa am douleur ci ventre bi depuis trois days, te fièvre du. »

Ici : wolof → français (« douleur », « ventre », « depuis », « days ») → wolof
(« fièvre du » = pas de fièvre).

## Suite d'évaluation

`app/services/ai/eval_cases.py` contient 10 cas documentés, couvrant :

| Cas | Langue | Invariant |
| --- | --- | --- |
| wo-001 | wolof+fr | douleur conservée ; « fièvre du » = négation ; aucune dose |
| fr-002 | fr | « sans fièvre », « pas de vomissements » non positifs |
| wo-003 | wolof | « xamuma » conserve l'incertitude |
| med-004 | fr | 5 mg ≠ 50 mg |
| med-005 | fr | 0,5 mg ≠ 5 ml |
| neg-006 | fr | « pas d'allergie » reste une négation |
| date-007 | wo+fr | durée conservée, aucune date absolue inventée |
| noise-008 | wolof | bruit → aucune donnée inventée |
| acc-009 | fr | accents normalisés, 38,5 exact |
| absent-010 | fr | absence → « Non documenté » |

Ces cas sont exécutés par `backend/tests/test_wolof_eval.py` et exposés par
`GET /api/scribe/wolof-eval`.

## Traitement des nombres

Les nombres sont traités avec une vigilance maximale (doses) :

- « 5 mg » et « 50 mg » sont distingués exactement.
- « 0,5 mg » est normalisé en « 0.5 mg ».
- Une dose qui n'apparaît pas littéralement dans la source est **retirée** et
  marquée « À vérifier ».

## Transcription originale

Lorsque le cadre légal et le consentement le permettent, sont conservés :

- l'audio original (`ai_transcriptions.audio_ref`, uniquement si
  `consent_audio` est vrai) ;
- la transcription brute ;
- la transcription corrigée ;
- la structure IA ;
- la note validée.

Le professionnel peut comparer ces éléments.

## Limites (documentées honnêtement)

- **Aucun moteur de reconnaissance vocale wolof réel n'est configuré.** La
  transcription audio n'est donc **pas disponible** ; le mode démonstration
  accepte une transcription saisie.
- Le glossaire de traduction est **illustratif**, non un traducteur complet.
- La couverture lexicale du wolof est partielle ; les cas non reconnus ne
  produisent rien (jamais d'invention).
- Une évaluation clinique du wolof avec des locuteurs natifs **reste à valider**.
