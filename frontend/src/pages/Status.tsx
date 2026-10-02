import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";
import { useMeta } from "../lib/useMeta";
import { CapabilityBadge, type CapabilityState } from "../components/ui";
import { IconWarning, IconArrowLeft } from "../components/icons";

/**
 * Public status page. Distinguishes RÉEL / DÉMO / PARTIEL / NON CONNECTÉ / À VALIDER.
 * This page is the platform's honesty contract.
 */
const ROWS: Array<{ label: string; state: CapabilityState; note: string }> = [
  { label: "Authentification (inscription, connexion, MFA TOTP)", state: "REEL", note: "Fonctionne." },
  { label: "RBAC par ressource + audit + break-glass", state: "REEL", note: "Fonctionne." },
  { label: "Dossier patient (permissions)", state: "REEL", note: "Fonctionne." },
  { label: "Chaîne Scribe (transcrire → structurer → vérifier → valider)", state: "DEMO", note: "Extraction déterministe, données synthétiques." },
  { label: "Garde-fous anti-hallucination", state: "REEL", note: "Règles déterministes, testées." },
  { label: "Reconnaissance vocale Wolof (STT)", state: "NON_CONNECTE", note: "Aucun moteur vocal réel configuré." },
  { label: "Traduction Wolof ↔ Français", state: "DEMO", note: "Glossaire illustratif uniquement." },
  { label: "Téléconsultation vidéo (WebRTC/ICE)", state: "NON_CONNECTE", note: "Architecture prête, serveurs ICE absents." },
  { label: "Messagerie interne", state: "REEL", note: "Fonctionne, permissions strictes." },
  { label: "Documents versionnés", state: "REEL", note: "Fonctionne." },
  { label: "Coordination des soins / orientations", state: "REEL", note: "Fonctionne, traçable." },
  { label: "Mode offline (file de synchronisation)", state: "PARTIEL", note: "File locale prête, reprise à finaliser." },
  { label: "Paiements (Wave, Orange Money, carte)", state: "NON_CONNECTE", note: "Abstraction prête, clés serveur absentes." },
  { label: "Notifications WhatsApp", state: "NON_CONNECTE", note: "Prévu, non implémenté." },
  { label: "Conformité réglementaire Sénégal", state: "A_VALIDER", note: "Nécessite validation juridique." },
];

export function Status() {
  const { meta, error } = useMeta();
  return (
    <div className="min-h-screen bg-hero">
      <div className="mx-auto max-w-4xl px-4 py-10">
        <Link to="/" className="mb-6 inline-block">
          <Logo />
        </Link>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">
          État des fonctionnalités
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-muted">
          Transparence : chaque fonctionnalité est classée RÉEL (fonctionne), DÉMO (données
          synthétiques), PARTIEL (nécessite configuration), NON CONNECTÉ (architecture prête, service
          externe absent) ou À VALIDER (validation requise).
        </p>

        {error && (
          <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-orange-300 bg-orange-50 px-4 py-3 text-sm text-orange-900">
            <IconWarning className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <p>
              Backend non connecté depuis ce déploiement. Les fonctionnalités serveur sont
              indisponibles tant que l'API n'est pas configurée (variable VITE_API_BASE).
            </p>
          </div>
        )}

        <ul className="mt-6 space-y-2.5">
          {ROWS.map((r) => (
            <li key={r.label} className="card flex flex-col gap-2 p-4 sm:flex-row sm:items-center">
              <span className="flex-1 text-sm font-medium text-ink">{r.label}</span>
              <span className="shrink-0">
                <CapabilityBadge state={r.state} />
              </span>
              <span className="text-sm text-muted sm:w-64 sm:shrink-0">{r.note}</span>
            </li>
          ))}
        </ul>

        {meta && (
          <p className="mt-4 text-xs text-muted">
            Mode IA : {meta.ai_mode} · Mode paiement : {meta.payment_mode}
          </p>
        )}

        <div className="mt-8">
          <Link to="/" className="btn-secondary">
            <IconArrowLeft className="h-4 w-4" aria-hidden="true" />
            Retour à l'accueil
          </Link>
        </div>
      </div>
    </div>
  );
}
