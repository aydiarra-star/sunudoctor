import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  IconCheckCircle,
  IconClose,
  IconDot,
  IconInfo,
  IconOffline,
  IconOnline,
  IconLimited,
  IconWarning,
  IconLock,
} from "./icons";

export type State = "loading" | "error" | "empty" | "success" | "offline" | "denied" | "pending";

/* ---------------------------------------------------------------- Skeletons */

export function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
  return <span className={`skeleton block ${className}`} aria-hidden="true" />;
}

/** Generic list skeleton — used while data loads, never a bare "Loading…". */
export function ListSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3" role="status" aria-live="polite" aria-label="Chargement en cours">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="card flex items-center gap-4">
          <Skeleton className="h-11 w-11 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1 space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
          </div>
          <Skeleton className="h-8 w-20 shrink-0 rounded-lg" />
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`card space-y-3 ${className}`} role="status" aria-label="Chargement">
      <Skeleton className="h-5 w-1/2" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-3/4" />
    </div>
  );
}

/* ------------------------------------------------------------------ Spinner */

export function Spinner({ label = "Chargement…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-muted" role="status" aria-live="polite">
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-primary/25 border-t-primary"
        aria-hidden="true"
      />
      <span className="text-sm">{label}</span>
    </div>
  );
}

/* ------------------------------------------------------------- Empty states */

export function EmptyState({
  title,
  hint,
  icon,
  action,
}: {
  title: string;
  hint?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="card flex flex-col items-center border-dashed px-6 py-10 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-50 text-primary">
        {icon ?? <IconDot className="h-6 w-6" aria-hidden="true" />}
      </span>
      <p className="mt-4 font-semibold text-ink">{title}</p>
      {hint && <p className="mt-1 max-w-sm text-sm text-muted">{hint}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/* ------------------------------------------------------------ Error / denied */

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card flex items-start gap-3 border-red-200 bg-red-50" role="alert">
      <IconWarning className="mt-0.5 h-5 w-5 shrink-0 text-red-600" aria-hidden="true" />
      <div className="min-w-0">
        <p className="font-semibold text-red-800">Impossible de charger les données pour le moment</p>
        <p className="mt-1 text-sm text-red-700">{message}</p>
        {onRetry && (
          <button className="btn-secondary mt-3" onClick={onRetry}>
            Réessayer
          </button>
        )}
      </div>
    </div>
  );
}

export function DeniedState({ message }: { message: string }) {
  return (
    <div className="card flex items-start gap-3 border-orange-200 bg-orange-50" role="alert">
      <IconLock className="mt-0.5 h-5 w-5 shrink-0 text-orange-600" aria-hidden="true" />
      <div>
        <p className="font-semibold text-orange-800">Permission refusée</p>
        <p className="mt-1 text-sm text-orange-700">{message}</p>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------- Page header */

export function PageHeader({
  title,
  subtitle,
  actions,
  icon,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex items-start gap-3">
        {icon && (
          <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-primary">
            {icon}
          </span>
        )}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">{title}</h1>
          {subtitle && <p className="mt-1 max-w-2xl text-sm text-muted">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

/* ------------------------------------------------------- Capability taxonomy */

export type CapabilityState = "REEL" | "DEMO" | "PARTIEL" | "NON_CONNECTE" | "A_VALIDER";

const CAPABILITY_META: Record<
  CapabilityState,
  { label: string; cls: string; Icon: typeof IconCheckCircle; hint: string }
> = {
  REEL: {
    label: "RÉEL",
    cls: "badge-real",
    Icon: IconCheckCircle,
    hint: "Fonctionne réellement et est testé.",
  },
  DEMO: {
    label: "DÉMO",
    cls: "badge-warn",
    Icon: IconInfo,
    hint: "Fonctionne avec des données synthétiques clairement identifiées.",
  },
  PARTIEL: {
    label: "PARTIEL",
    cls: "badge-partial",
    Icon: IconLimited,
    hint: "Fonctionne mais nécessite une configuration.",
  },
  NON_CONNECTE: {
    label: "NON CONNECTÉ",
    cls: "badge-unconnected",
    Icon: IconOffline,
    hint: "Architecture prête, service externe absent.",
  },
  A_VALIDER: {
    label: "À VALIDER",
    cls: "badge-validate",
    Icon: IconInfo,
    hint: "Nécessite une validation juridique, clinique ou institutionnelle.",
  },
};

/**
 * Status badge. Colour is never the only signal: every badge carries an icon
 * and a text label so it stays readable for colour-blind users and screen
 * readers.
 */
export function CapabilityBadge({
  state,
  withTooltip = true,
}: {
  state: CapabilityState;
  withTooltip?: boolean;
}) {
  const meta = CAPABILITY_META[state];
  const Icon = meta.Icon;
  return (
    <span className={meta.cls} title={withTooltip ? meta.hint : undefined}>
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {meta.label}
    </span>
  );
}

/* ----------------------------------------------------------- Connection pill */

export type Connection = "online" | "limited" | "offline";

export function ConnectionPill({ status, label }: { status: Connection; label?: string }) {
  const map: Record<Connection, { cls: string; Icon: typeof IconOnline; text: string }> = {
    online: { cls: "text-emerald-700", Icon: IconOnline, text: label ?? "Connecté" },
    limited: { cls: "text-amber-700", Icon: IconLimited, text: label ?? "Connexion limitée" },
    offline: { cls: "text-red-700", Icon: IconOffline, text: label ?? "Hors ligne" },
  };
  const { cls, Icon, text } = map[status];
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${cls}`}>
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {text}
    </span>
  );
}

/* ------------------------------------------------------------------- Toasts */

interface Toast {
  id: string;
  title: string;
  body?: string;
  tone: "success" | "info" | "error";
}

interface ToastContextValue {
  push: (t: Omit<Toast, "id">) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const remove = useCallback((id: string) => {
    setToasts((list) => list.filter((t) => t.id !== id));
    clearTimeout(timers.current[id]);
    delete timers.current[id];
  }, []);

  const push = useCallback(
    (t: Omit<Toast, "id">) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setToasts((list) => [...list, { ...t, id }]);
      timers.current[id] = setTimeout(() => remove(id), 4500);
    },
    [remove],
  );

  useEffect(() => {
    const t = timers.current;
    return () => Object.values(t).forEach(clearTimeout);
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-4 z-[60] flex flex-col items-center gap-2 px-4 sm:bottom-6 sm:right-6 sm:left-auto sm:items-end"
        role="region"
        aria-label="Notifications"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className="pointer-events-auto flex w-full max-w-sm animate-fade-in-up items-start gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-elevated"
            role="status"
          >
            <span
              className={
                t.tone === "success"
                  ? "text-emerald-600"
                  : t.tone === "error"
                    ? "text-red-600"
                    : "text-primary"
              }
            >
              {t.tone === "error" ? (
                <IconWarning className="h-5 w-5" aria-hidden="true" />
              ) : (
                <IconCheckCircle className="h-5 w-5" aria-hidden="true" />
              )}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-ink">{t.title}</p>
              {t.body && <p className="mt-0.5 text-xs text-muted">{t.body}</p>}
            </div>
            <button
              className="text-muted hover:text-ink"
              onClick={() => remove(t.id)}
              aria-label="Fermer la notification"
            >
              <IconClose className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  return ctx ?? { push: () => undefined };
}

/* -------------------------------------------------------------- Status pill */

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

/* -------------------------------------------------- Verification badge */

const BADGE_TONE_CLASS: Record<string, string> = {
  success: "badge-ok",
  info: "badge-info",
  warning: "badge-warn",
  danger: "badge-danger",
  neutral: "badge-muted",
};

/**
 * Professional verification badge. The wording comes from the backend so the UI
 * can never claim a stronger verification than the data supports.
 */
export function VerificationBadgePill({
  badge,
}: {
  badge: { label: string; tone: string; verified_by?: string | null; note?: string } | null | undefined;
}) {
  if (!badge) return <span className="badge-muted">Vérification non documentée</span>;
  return (
    <span className={BADGE_TONE_CLASS[badge.tone] ?? "badge-muted"} title={badge.note ?? undefined}>
      {badge.label}
    </span>
  );
}

/* --------------------------------------------------------- Demo banner */

/** Bandeau "Mode démonstration" — always shown when capabilities are synthetic. */
export function DemoBanner({ capabilities }: { capabilities?: Record<string, string> }) {
  const notConnected = capabilities
    ? Object.entries(capabilities).filter(
        ([, v]) => v === "non_connecte" || v === "configuration_requise",
      )
    : [];
  return (
    <div
      className="mb-4 flex items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      role="status"
    >
      <IconInfo className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" aria-hidden="true" />
      <div>
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
    </div>
  );
}

/* ------------------------------------------------------------------ Avatar */

const AVATAR_TONES = [
  "bg-primary-100 text-primary-800",
  "bg-emerald-100 text-emerald-800",
  "bg-amber-100 text-amber-800",
  "bg-violet-100 text-violet-800",
  "bg-sky-100 text-sky-800",
  "bg-rose-100 text-rose-800",
];

export function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function Avatar({ name, size = 40 }: { name: string; size?: number }) {
  const initials = initialsOf(name);
  const tone = AVATAR_TONES[initials.charCodeAt(0) % AVATAR_TONES.length];
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full font-semibold ${tone}`}
      style={{ width: size, height: size, fontSize: size * 0.38 }}
      aria-hidden="true"
    >
      {initials}
    </span>
  );
}
