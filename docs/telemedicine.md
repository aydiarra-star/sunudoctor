# Téléconsultation — SunuDoctor

## Fonctions prévues

- Demande de téléconsultation
- Acceptation / refus
- Vidéo
- Audio
- Chat
- Partage de documents
- Scribe pendant la consultation
- Accès au dossier patient
- Compte rendu

## État réel

| Fonction | État |
| --- | --- |
| Création / suivi de téléconsultation | RÉEL |
| Chat et messagerie | RÉEL |
| Documents | RÉEL |
| Scribe pendant la consultation | DÉMO |
| Compte rendu | RÉEL |
| **Vidéo / audio temps réel** | **NON CONNECTÉ** |

## Vidéo — configuration requise

L'API expose `GET /api/teleconsultations/ice-servers`, qui renvoie :

```json
{ "configured": false, "ice_servers": [] }
```

Aucun service vidéo réel (WebRTC avec serveurs STUN/TURN) n'est connecté. L'UI
affiche donc explicitement **« Vidéo — configuration requise »** et ne prétend
jamais qu'un appel est actif.

### Pour activer la vidéo

1. Déployer un service de signalisation WebRTC.
2. Fournir des serveurs ICE (STUN/TURN) réels.
3. Configurer les variables correspondantes côté serveur.
4. Mettre `provider="webrtc"` sur les téléconsultations concernées.

L'architecture est prête : le champ `provider` et la route ICE existent, mais
restent inertes tant qu'aucun service réel n'est fourni.

## WhatsApp

Une architecture de notification pourra intégrer WhatsApp (rappels, liens), mais
l'application **ne dépend pas** de WhatsApp et ne prétend pas y être connectée.
