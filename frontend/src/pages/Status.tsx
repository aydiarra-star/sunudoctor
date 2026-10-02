import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";
import { useMeta } from "../lib/useMeta";

/**
 * Public status page. Distinguishes RÉEL / DÉMO / PARTIEL / NON CONNECTÉ.
 * This page is the platform's honesty contract.
 */
const ROWS: Array<{ label: string; state: string; note: string }> = [
  { label: "Authentification (inscription, connexion, MFA TOTP)", state: "RÉEL", note: "Fonctionne." },
  { label: "RBAC par ressource + audit + break-glass", state: "RÉEL", note: "Fonctionne." },
  { label: "Dossier patient (permissions)", state: "RÉEL", note: "Fonctionne." },
  { label: "Chaîne Scribe (transcrire → structurer → vérifier → valider)", state: "DÉMO", note: "Extraction déterministe, données synthétiques." },
  { label: "Garde-fous anti-hallucination", state: "RÉEL", note: "Règles déterministes, testées." },
  { label: "Reconnaissance vocale Wolof (STT)", state: "NON CONNECTÉ", note: "Aucun moteur vocal réel configuré." },
  { label: "Traduction Wolof ↔ Français", state: "DÉMO", note: "Glossaire illustratif uniquement." },
  { label: "Téléconsultation vidéo (WebRTC/ICE)", state: "NON CONNECTÉ", note: "Architecture prête, serveurs ICE absents." },
  { label: "Messagerie interne", state: "RÉEL", note: "Fonctionne, permissions strictes." },
  { label: "Documents versionnés", state: "RÉEL", note: "Fonctionne." },
  { label: "Coordination des soins / orientations", state: "RÉEL", note: "Fonctionne, traçable." },
  { label: "Mode offline (file de synchronisation)", state: "PARTIEL", note: "File locale prête, reprise à finaliser." },
  { label: "Paiements (Wave, Orange Money, carte)", state: "NON CONNECTÉ", note: "Abstraction prête, clés serveur absentes." },
  { label: "Notifications WhatsApp", state: "NON CONNECTÉ", note: "Prévu, non implémenté." },
  { label: "Conformité réglementaire Sénégal", state: "À VALIDER", note: "Nécessite validation juridique." },
];

const COLORS: Record<string, string> = {
  "RÉEL": "badge-ok",
  "DÉMO": "badge-warn",
  PARTIEL: "badge-info",
  "NON CONNECTÉ": "badge-muted",
  "À VALIDER": "badge-info",
};

export function Status() {
  const { meta, error } = useMeta();
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <Link to="/" className="mb-6 inline-block">
        <Logo />
      </Link>
      <h1 className="text-2xl font-bold text-ink">État des fonctionnalités</h1>
      <p className="mt-2 text-sm text-muted">
        Transparence : chaque fonctionnalité est classée RÉEL (fonctionne), DÉMO (données
        synthétiques), PARTIEL (nécessite configuration) ou NON CONNECTÉ (architecture prête, service
        externe absent).
      </p>

      {error && (
        <p className="mt-4 rounded-xl border border-orange-300 bg-orange-50 px-4 py-3 text-sm text-orange-900">
          Backend non connecté depuis ce déploiement. Les fonctionnalités serveur sont indisponibles
          tant que l'API n'est pas configurée (variable VITE_API_BASE).
        </p>
      )}

      <div className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[36rem] text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase text-muted">
              <th className="py-2 pr-4">Fonctionnalité</th>
              <th className="py-2 pr-4">Statut</th>
              <th className="py-2">Détail</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.label} className="border-b border-slate-100">
                <td className="py-2 pr-4 text-ink">{r.label}</td>
                <td className="py-2 pr-4">
                  <span className={COLORS[r.state] ?? "badge-muted"}>{r.state}</span>
                </td>
                <td className="py-2 text-muted">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {meta && (
        <p className="mt-4 text-xs text-muted">
          Mode IA : {meta.ai_mode} · Mode paiement : {meta.payment_mode}
        </p>
      )}

      <div className="mt-8">
        <Link to="/" className="btn-secondary">
          Retour à l'accueil
        </Link>
      </div>
    </div>
  );
}
