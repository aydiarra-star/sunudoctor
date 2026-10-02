# IA clinique — SunuDoctor

## Règle fondatrice

**ZÉRO INVENTION.** L'IA ne crée jamais de diagnostic, symptôme, médicament,
dose, allergie, antécédent, résultat, constante, grossesse ou identité. Si
l'information est absente : « Non documenté ». Si elle est incertaine :
« À vérifier ».

## Les quatre interfaces

```python
class SpeechToTextProvider(ABC):    # audio -> texte
class ClinicalAIProvider(ABC):      # texte -> note structurée (extraction)
class TranslationProvider(ABC):     # wolof <-> français
class SafetyProvider(ABC):          # garde-fous post-traitement
```

Aucune partie de l'application n'est couplée à un fournisseur particulier.
`services/ai/factory.py` sélectionne le fournisseur selon la configuration et
signale tout repli en mode démonstration.

## Le moteur de sécurité (`services/ai/safety.py`)

C'est le composant qui garantit l'absence d'invention. Il applique :

### 1. Ancrage (grounding)

Toute valeur clinique doit être traçable dans la transcription source. Une
valeur non ancrée est **supprimée** et signalée. Les nombres doivent
correspondre exactement.

### 2. Négation

« pas de fièvre », « sans fièvre », « n'a pas », « aucune », « amul », « du »
(wolof) sont détectés. Une négation ne devient **jamais** un symptôme positif ;
elle est conservée dans `negated_symptoms`.

### 3. Incertitude

« je ne sais pas », « xamuma », « peut-être » sont conservés comme incertains.
L'incertitude n'est jamais convertie en valeur.

### 4. Absence ≠ négation

Une information absente devient « Non documenté », jamais une négation ni un
positif.

### 5. Diagnostic interdit

Le diagnostic produit par l'IA est systématiquement retiré : il doit être saisi
par le professionnel.

## Pipeline

| Étape | Endpoint | Sortie |
| --- | --- | --- |
| Transcrire | `POST /api/scribe/transcribe` | texte brut + drapeau démo |
| Structurer | `POST /api/scribe/structure` | note structurée + drapeaux de sécurité |
| Vérifier | (inclus dans structure) | `safety_flags`, `uncertainties` |
| Valider | `POST /api/scribe/consultations/{id}/validate` | version + validation humaine |

## Statut « BROUILLON IA »

Toute note générée porte le statut `draft_ai` et l'avertissement :

> Cette note a été générée avec l'aide de l'IA. Vérifiez son exactitude avant
> validation.

Elle ne devient `validated` qu'après action explicite d'un professionnel.

## Mode démonstration

En l'absence de clés de fournisseur réel, les fournisseurs de démonstration sont
utilisés. Ils sont **déterministes et strictement extractifs** : chaque valeur
produite est une sous-chaîne littérale de l'entrée. Ils ne peuvent donc pas
inventer, mais ils ne comprennent pas non plus le langage naturel. Toute sortie
est marquée `is_demo=True` et affichée comme « Mode démonstration ».

## Limites

- Aucune compréhension sémantique réelle en mode démonstration.
- L'extraction repose sur des lexiques ; des formulations inattendues peuvent
  ne rien extraire (ce qui est préférable à une invention).
- La transcription vocale réelle n'est pas disponible sans moteur STT dédié.
