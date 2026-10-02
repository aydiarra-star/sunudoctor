import type { ReactNode } from "react";

export type State = "loading" | "error" | "empty" | "success" | "offline" | "denied" | "pending";

export function Spinner({ label = "Chargement…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-muted" role="status" aria-live="polite">
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-primary/30 border-t-primary"
        aria-hidden="true"
      />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card border-red-200 bg-red-50" role="alert">
      <p className="font-semibold text-red-800">Une erreur est survenue</p>
      <p className="mt-1 text-sm text-red-700">{message}</p>
      {onRetry && (
        <button className="btn-secondary mt-3" onClick={onRetry}>
          Réessayer
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="card border-dashed text-center">
      <p className="font-semibold text-ink">{title}</p>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
    </div>
  );
}

export function DeniedState({ message }: { message: string }) {
  return (
    <div className="card border-orange-200 bg-orange-50" role="alert">
      <p className="font-semibold text-orange-800">Permission refusée</p>
      <p className="mt-1 text-sm text-orange-700">{message}</p>
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold text-ink sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

/** Bandeau "Mode démonstration" — always shown when capabilities are synthetic. */
export function DemoBanner({ capabilities }: { capabilities?: Record<string, string> }) {
  const notConnected = capabilities
    ? Object.entries(capabilities).filter(([, v]) => v === "non_connecte" || v === "configuration_requise")
    : [];
  return (
    <div
      className="mb-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      role="status"
    >
      <p className="font-semibold">Mode démonstration</p>
      <p className="mt-0.5">
        Les fonctions d'IA utilisent des données synthétiques. Aucun service d'IA réel n'est
        connecté. Vérifiez toujours les informations cliniques.
      </p>
      {notConnected.length > 0 && (
        <p className="mt-1 text-xs">
          Non connecté : {notConnected.map(([k]) => k.replaceAll("_", " ")).join(", ")}.
        </p>
      )}
    </div>
  );
}

export function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    verified: "badge-ok",
    validated: "badge-ok",
    in_review: "badge-info",
    pending: "badge-warn",
    to_complete: "badge-warn",
    refused: "badge-muted",
    draft: "badge-muted",
    draft_ai: "badge-warn",
    requested: "badge-info",
    trial: "badge-info",
  };
  const labels: Record<string, string> = {
    verified: "Vérifié",
    validated: "Validé",
    in_review: "En cours",
    pending: "En attente",
    to_complete: "À compléter",
    refused: "Refusé",
    draft: "Brouillon",
    draft_ai: "Brouillon IA",
    requested: "Demandé",
    trial: "Essai",
  };
  return <span className={map[status] ?? "badge-muted"}>{labels[status] ?? status}</span>;
}
