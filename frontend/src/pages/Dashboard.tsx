import { Link } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import { useAuth } from "../lib/auth";
import { useMeta } from "../lib/useMeta";
import { Avatar, PageHeader, StatusPill } from "../components/ui";
import {
  IconScribe,
  IconAdd,
  IconTeleconsultation,
  IconDocuments,
  IconMessages,
  IconSearch,
  IconArrowRight,
  IconWarning,
  IconLanguage,
  IconVitals,
  IconCalendar,
  IconSecurity,
  IconCheckCircle,
} from "../components/icons";

interface QuickAction {
  to: string;
  label: string;
  body: string;
  Icon: LucideIcon;
  tone: string;
}

const PROFESSIONAL_ACTIONS: QuickAction[] = [
  {
    to: "/app/scribe",
    label: "Nouvelle consultation",
    body: "Démarrer le Scribe clinique",
    Icon: IconScribe,
    tone: "bg-primary-100 text-primary-800",
  },
  {
    to: "/app/patients",
    label: "Nouveau patient",
    body: "Créer un dossier",
    Icon: IconAdd,
    tone: "bg-emerald-100 text-emerald-800",
  },
  {
    to: "/app/teleconsultation",
    label: "Téléconsultation",
    body: "Vidéo — configuration requise",
    Icon: IconTeleconsultation,
    tone: "bg-sky-100 text-sky-800",
  },
  {
    to: "/app/documents",
    label: "Documents",
    body: "Comptes rendus, prescriptions",
    Icon: IconDocuments,
    tone: "bg-violet-100 text-violet-800",
  },
  {
    to: "/app/messages",
    label: "Messages",
    body: "Messagerie sécurisée",
    Icon: IconMessages,
    tone: "bg-amber-100 text-amber-800",
  },
  {
    to: "/app/patients",
    label: "Rechercher",
    body: "Trouver un dossier patient",
    Icon: IconSearch,
    tone: "bg-slate-100 text-slate-700",
  },
];

const PATIENT_ACTIONS: QuickAction[] = [
  {
    to: "/app/appointments",
    label: "Rendez-vous",
    body: "Demander ou consulter",
    Icon: IconCalendar,
    tone: "bg-primary-100 text-primary-800",
  },
  {
    to: "/app/documents",
    label: "Mes documents",
    body: "Comptes rendus, prescriptions",
    Icon: IconDocuments,
    tone: "bg-violet-100 text-violet-800",
  },
  {
    to: "/app/teleconsultation",
    label: "Téléconsultation",
    body: "Vidéo — configuration requise",
    Icon: IconTeleconsultation,
    tone: "bg-sky-100 text-sky-800",
  },
  {
    to: "/app/consents",
    label: "Mes consentements",
    body: "Accès, partage, IA",
    Icon: IconSecurity,
    tone: "bg-emerald-100 text-emerald-800",
  },
];

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Bonjour";
  if (h < 18) return "Bon après-midi";
  return "Bonsoir";
}

function QuickCard({ action }: { action: QuickAction }) {
  const { to, label, body, Icon, tone } = action;
  return (
    <Link to={to} className="card card-hover flex items-center gap-4">
      <span className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${tone}`}>
        <Icon className="h-6 w-6" aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block font-semibold text-ink">{label}</span>
        <span className="block truncate text-sm text-muted">{body}</span>
      </span>
      <IconArrowRight className="h-4 w-4 shrink-0 text-slate-300" aria-hidden="true" />
    </Link>
  );
}

export function Dashboard() {
  const { user } = useAuth();
  const { meta } = useMeta();
  const isPatient = user?.role === "patient";
  const actions = isPatient ? PATIENT_ACTIONS : PROFESSIONAL_ACTIONS;
  const verification = user?.professional?.verification_status;

  return (
    <div>
      <PageHeader
        title={`${greeting()} ${user?.full_name?.split(" ").slice(-1)[0] ?? ""}`}
        subtitle="Votre espace de travail clinique"
        actions={
          !isPatient && (
            <Link to="/app/scribe" className="btn-primary">
              <IconScribe className="h-4 w-4" aria-hidden="true" />
              Démarrer le Scribe
            </Link>
          )
        }
      />

      {/* Identity + connection summary */}
      <div className="mb-6 flex flex-wrap items-center gap-4 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-soft">
        <Avatar name={user?.full_name ?? "?"} size={48} />
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-ink">{user?.full_name}</p>
          <p className="text-sm text-muted">{user?.email}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {user?.professional && <StatusPill status={user.professional.verification_status} />}
          {meta && (
            <span className="badge-info">
              <IconLanguage className="h-3 w-3" aria-hidden="true" />
              Wolof + Français
            </span>
          )}
        </div>
      </div>

      {verification && verification !== "verified" && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-orange-300 bg-orange-50 px-4 py-3 text-sm text-orange-900">
          <IconWarning className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-semibold">Vérification professionnelle : en cours</p>
            <p className="mt-0.5">
              Le statut « Vérifié » n'est jamais attribué automatiquement. Statut actuel :{" "}
              <strong>{verification}</strong>.
            </p>
          </div>
        </div>
      )}

      {/* Quick actions */}
      <section aria-labelledby="qa-title">
        <h2 id="qa-title" className="section-title mb-3">
          Actions rapides
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {actions.map((a) => (
            <QuickCard key={`${a.to}-${a.label}`} action={a} />
          ))}
        </div>
      </section>

      {/* Workspace overview */}
      <section className="mt-8 grid gap-4 lg:grid-cols-3" aria-labelledby="ws-title">
        <h2 id="ws-title" className="sr-only">
          Vue d'ensemble
        </h2>

        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-ink">Consultations récentes</h3>
            <Link to="/app/consultations" className="text-sm font-medium text-primary">
              Tout voir
            </Link>
          </div>
          <div className="mt-4 flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 px-4 py-8 text-center">
            <IconVitals className="h-7 w-7 text-slate-300" aria-hidden="true" />
            <p className="mt-2 text-sm font-medium text-ink">Aucune consultation pour le moment</p>
            <p className="mt-1 text-xs text-muted">
              Démarrez le Scribe pour créer votre première consultation.
            </p>
            <Link to="/app/scribe" className="btn-primary mt-4">
              <IconScribe className="h-4 w-4" aria-hidden="true" />
              Nouvelle consultation
            </Link>
          </div>
        </div>

        <div className="card">
          <h3 className="font-semibold text-ink">Confiance &amp; sécurité</h3>
          <ul className="mt-3 space-y-3 text-sm">
            <li className="flex items-start gap-2.5">
              <IconCheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
              <span className="text-muted">
                <strong className="text-ink">Vérification humaine</strong> — l'IA ne valide jamais
                une note.
              </span>
            </li>
            <li className="flex items-start gap-2.5">
              <IconCheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
              <span className="text-muted">
                <strong className="text-ink">Zéro invention</strong> — absent = « Non documenté ».
              </span>
            </li>
            <li className="flex items-start gap-2.5">
              <IconSecurity className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
              <span className="text-muted">
                <strong className="text-ink">Traçabilité</strong> — chaque accès est audité.
              </span>
            </li>
          </ul>
          <Link to="/status" className="btn-secondary mt-4 w-full">
            État des fonctionnalités
          </Link>
        </div>
      </section>
    </div>
  );
}
