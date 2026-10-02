import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import {
  Avatar,
  EmptyState,
  ErrorState,
  ListSkeleton,
  PageHeader,
  StatusPill,
  useToast,
} from "../components/ui";
import {
  IconMessages,
  IconDocuments,
  IconCoordination,
  IconCalendar,
  IconTeleconsultation,
  IconSecurity,
  IconNotifications,
  IconProfile,
  IconSettings,
  IconWarning,
  IconLanguage,
  IconExternalLink,
} from "../components/icons";

interface ListState<T> {
  data: T[] | null;
  error: string | null;
  reload: () => void;
}

function useList<T>(path: string): ListState<T> {
  const [data, setData] = useState<T[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    setError(null);
    api
      .get<T[]>(path)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, [path, nonce]);

  return { data, error, reload: () => setNonce((n) => n + 1) };
}

/** Honest, illustrated list page used by several sections. */
function ListPage<T>({
  title,
  subtitle,
  path,
  emptyTitle,
  emptyHint,
  emptyIcon,
  render,
  notice,
  headerIcon,
  actions,
}: {
  title: string;
  subtitle: string;
  path: string;
  emptyTitle: string;
  emptyHint?: string;
  emptyIcon?: ReactNode;
  render: (item: T) => ReactNode;
  notice?: ReactNode;
  headerIcon?: ReactNode;
  actions?: ReactNode;
}) {
  const { data, error, reload } = useList<T>(path);
  return (
    <div>
      <PageHeader title={title} subtitle={subtitle} icon={headerIcon} actions={actions} />
      {notice && (
        <div className="mb-4 flex items-start gap-2.5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-muted">
          <IconWarning className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" aria-hidden="true" />
          <div>{notice}</div>
        </div>
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {!error && data === null && <ListSkeleton rows={3} />}
      {!error && data?.length === 0 && (
        <EmptyState icon={emptyIcon} title={emptyTitle} hint={emptyHint} />
      )}
      {!error && data && data.length > 0 && (
        <ul className="space-y-2.5">
          {data.map((item, i) => (
            <li key={i} className="card card-hover">
              {render(item)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface MessageItem {
  id: string;
  body: string;
  created_at: string;
  read: boolean;
}

export function Messages() {
  return (
    <ListPage<MessageItem>
      title="Messages"
      subtitle="Messagerie interne sécurisée. Permissions strictes."
      headerIcon={<IconMessages className="h-5 w-5" aria-hidden="true" />}
      path="/messages"
      emptyTitle="Aucun message"
      emptyHint="Les échanges liés à vos dossiers autorisés apparaîtront ici."
      emptyIcon={<IconMessages className="h-6 w-6" aria-hidden="true" />}
      notice="Les messages sont limités aux personnes autorisées sur le dossier concerné."
      render={(m) => (
        <div className="flex items-start gap-3">
          <span
            className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${m.read ? "bg-slate-300" : "bg-primary"}`}
            aria-hidden="true"
          />
          <div className="min-w-0 flex-1">
            <p className="text-sm text-ink">{m.body}</p>
            <p className="mt-1 text-xs text-muted">
              {new Date(m.created_at).toLocaleString("fr-FR")} · {m.read ? "Lu" : "Non lu"}
            </p>
          </div>
        </div>
      )}
    />
  );
}

interface DocumentItem {
  id: string;
  title: string;
  doc_type: string;
  status: string;
  version: number;
  is_demo: boolean;
}

export function Documents() {
  return (
    <ListPage<DocumentItem>
      title="Documents"
      subtitle="Comptes rendus, prescriptions, lettres, orientations. Chaque document est versionné."
      headerIcon={<IconDocuments className="h-5 w-5" aria-hidden="true" />}
      path="/documents"
      emptyTitle="Aucun document"
      emptyHint="Les comptes rendus et prescriptions validés apparaîtront ici."
      emptyIcon={<IconDocuments className="h-6 w-6" aria-hidden="true" />}
      render={(d) => (
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-100 text-violet-700">
              <IconDocuments className="h-5 w-5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="flex items-center gap-2 font-semibold text-ink">
                <span className="truncate">{d.title}</span>
                {d.is_demo && <span className="badge-demo shrink-0">DEMO</span>}
              </p>
              <p className="text-sm text-muted">
                {d.doc_type} · version {d.version}
              </p>
            </div>
          </div>
          <StatusPill status={d.status} />
        </div>
      )}
    />
  );
}

interface ReferralItem {
  id: string;
  patient_id: string;
  reason: string;
  priority: string;
  status: string;
  created_at: string;
}

export function Coordination() {
  return (
    <ListPage<ReferralItem>
      title="Coordination des soins"
      subtitle="Agent communautaire → Infirmier → Médecin → Spécialiste → Structure de référence."
      headerIcon={<IconCoordination className="h-5 w-5" aria-hidden="true" />}
      path="/referrals"
      emptyTitle="Aucune orientation"
      emptyHint="Les orientations entre professionnels et structures seront tracées ici."
      emptyIcon={<IconCoordination className="h-6 w-6" aria-hidden="true" />}
      notice="Chaque étape est traçable et auditée."
      render={(r) => (
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-semibold text-ink">{r.reason}</p>
            <p className="text-sm text-muted">
              Priorité {r.priority} · {new Date(r.created_at).toLocaleString("fr-FR")}
            </p>
          </div>
          <span className="badge-info shrink-0">{r.status}</span>
        </div>
      )}
    />
  );
}

interface AppointmentItem {
  id: string;
  patient_id: string;
  scheduled_at: string;
  status: string;
  channel: string;
  reason: string | null;
}

export function Appointments() {
  return (
    <ListPage<AppointmentItem>
      title="Rendez-vous"
      subtitle="Demandes, confirmations et rendez-vous planifiés."
      headerIcon={<IconCalendar className="h-5 w-5" aria-hidden="true" />}
      path="/appointments"
      emptyTitle="Aucun rendez-vous"
      emptyHint="Vos rendez-vous planifiés apparaîtront ici."
      emptyIcon={<IconCalendar className="h-6 w-6" aria-hidden="true" />}
      render={(a) => (
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="font-semibold text-ink">
              {new Date(a.scheduled_at).toLocaleString("fr-FR")}
            </p>
            <p className="text-sm text-muted">
              {a.channel === "teleconsultation" ? "Téléconsultation" : "Présentiel"}
              {a.reason ? ` · ${a.reason}` : ""}
            </p>
          </div>
          <span className="badge-info shrink-0">{a.status}</span>
        </div>
      )}
    />
  );
}

interface TeleItem {
  id: string;
  patient_id: string;
  status: string;
  provider: string;
  video_status: string;
}

export function Teleconsultation() {
  return (
    <div>
      <PageHeader
        title="Téléconsultation"
        subtitle="Rendez-vous, demande, acceptation, vidéo, audio, chat, documents, compte rendu."
        icon={<IconTeleconsultation className="h-5 w-5" aria-hidden="true" />}
      />
      <div className="mb-4 flex items-start gap-3 rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-700">
        <IconWarning className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" aria-hidden="true" />
        <div>
          <p className="font-semibold text-ink">Vidéo — configuration requise</p>
          <p className="mt-0.5">
            Aucun service vidéo réel (WebRTC/ICE) n'est connecté. L'architecture est prête : la
            vidéo sera activée dès qu'un serveur ICE sera configuré.
          </p>
        </div>
      </div>
      <TeleList />
    </div>
  );
}

function TeleList() {
  return (
    <ListPage<TeleItem>
      title=""
      subtitle=""
      path="/teleconsultations"
      emptyTitle="Aucune téléconsultation"
      emptyHint="Les demandes de téléconsultation apparaîtront ici."
      emptyIcon={<IconTeleconsultation className="h-6 w-6" aria-hidden="true" />}
      render={(t) => (
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="font-semibold text-ink">Téléconsultation</p>
            <p className="text-sm text-muted">Statut : {t.status}</p>
          </div>
          <span className={t.video_status === "pret" ? "badge-ok" : "badge-warn"}>
            {t.video_status === "pret" ? "Prêt" : "Vidéo — configuration requise"}
          </span>
        </div>
      )}
    />
  );
}

interface ConsentItem {
  id: string;
  scope: string;
  granted: boolean;
}

const CONSENT_LABELS: Record<string, string> = {
  access: "Accès au dossier",
  share: "Partage",
  teleconsultation: "Téléconsultation",
  audio: "Conservation audio",
  ai: "Assistance IA",
  research: "Recherche",
};

export function Consents({ patientId }: { patientId?: string }) {
  const [consents, setConsents] = useState<ConsentItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!patientId) return;
    setError(null);
    api
      .get<ConsentItem[]>(`/consents?patient_id=${patientId}`)
      .then(setConsents)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, [patientId]);

  return (
    <div>
      <PageHeader
        title="Mes consentements"
        subtitle="Accès, partage, téléconsultation, audio, IA, recherche."
        icon={<IconSecurity className="h-5 w-5" aria-hidden="true" />}
      />
      {!patientId && (
        <EmptyState
          icon={<IconSecurity className="h-6 w-6" aria-hidden="true" />}
          title="Sélectionnez un dossier patient"
          hint="Les consentements sont rattachés à un dossier patient."
          action={
            <Link to="/app/patients" className="btn-primary">
              Voir les patients
            </Link>
          }
        />
      )}
      {error && <ErrorState message={error} />}
      {patientId && consents === null && !error && <ListSkeleton rows={3} />}
      {patientId && consents?.length === 0 && (
        <EmptyState
          icon={<IconSecurity className="h-6 w-6" aria-hidden="true" />}
          title="Aucun consentement enregistré"
          hint="Les consentements du patient apparaîtront ici."
        />
      )}
      {consents && consents.length > 0 && (
        <ul className="space-y-2.5">
          {consents.map((c) => (
            <li key={c.id} className="card flex items-center justify-between">
              <span className="text-ink">{CONSENT_LABELS[c.scope] ?? c.scope}</span>
              <span className={c.granted ? "badge-ok" : "badge-muted"}>
                {c.granted ? "Accordé" : "Retiré"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface NotificationItem {
  id: string;
  title: string;
  body: string;
  created_at: string;
  read: boolean;
}

export function Notifications() {
  return (
    <ListPage<NotificationItem>
      title="Notifications"
      subtitle="Alertes de votre espace de travail."
      headerIcon={<IconNotifications className="h-5 w-5" aria-hidden="true" />}
      path="/notifications"
      emptyTitle="Aucune notification"
      emptyHint="Vos alertes (validation, partage, vérification) apparaîtront ici."
      emptyIcon={<IconNotifications className="h-6 w-6" aria-hidden="true" />}
      notice="Les notifications WhatsApp ne sont pas connectées (canal prévu, non actif)."
      render={(n) => (
        <div className="flex items-start gap-3">
          <span
            className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read ? "bg-slate-300" : "bg-primary"}`}
            aria-hidden="true"
          />
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-ink">{n.title}</p>
            <p className="text-sm text-muted">{n.body}</p>
            <p className="mt-1 text-xs text-muted">
              {new Date(n.created_at).toLocaleString("fr-FR")}
            </p>
          </div>
        </div>
      )}
    />
  );
}

export function Profile() {
  const [me, setMe] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Record<string, unknown>>("/auth/me")
      .then(setMe)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, []);

  const prof = (me?.professional ?? null) as Record<string, string> | null;
  const name = String(me?.full_name ?? "");

  return (
    <div>
      <PageHeader
        title="Profil"
        subtitle="Vos informations et votre statut de vérification."
        icon={<IconProfile className="h-5 w-5" aria-hidden="true" />}
      />
      {error && <ErrorState message={error} />}
      {!error && me === null && <ListSkeleton rows={2} />}
      {me && (
        <>
          <div className="card mb-4 flex items-center gap-4">
            <Avatar name={name} size={56} />
            <div className="min-w-0">
              <p className="text-lg font-semibold text-ink">{name}</p>
              <p className="text-sm text-muted">{String(me.email ?? "")}</p>
            </div>
            {prof && <StatusPill status={prof.verification_status} />}
          </div>
          <div className="card">
            <h2 className="font-semibold text-ink">Informations</h2>
            <dl className="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-xs font-semibold uppercase text-muted">Rôle</dt>
                <dd className="text-sm text-ink">{String(me.role ?? "")}</dd>
              </div>
              {prof && (
                <>
                  <div>
                    <dt className="text-xs font-semibold uppercase text-muted">Profession</dt>
                    <dd className="text-sm text-ink">{prof.profession}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold uppercase text-muted">Vérification</dt>
                    <dd className="text-sm text-ink">
                      <StatusPill status={prof.verification_status} />
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold uppercase text-muted">Numéro d'ordre</dt>
                    <dd className="text-sm text-ink">
                      {prof.license_number || "Non documenté"}
                    </dd>
                  </div>
                </>
              )}
            </dl>
          </div>
        </>
      )}
    </div>
  );
}

export function Settings() {
  const toast = useToast();
  return (
    <div>
      <PageHeader
        title="Paramètres"
        subtitle="Préférences du compte et sécurité."
        icon={<IconSettings className="h-5 w-5" aria-hidden="true" />}
      />
      <div className="card">
        <h2 className="font-semibold text-ink">Langue de travail</h2>
        <p className="mt-1 text-sm text-muted">
          Le Scribe est conçu pour le Wolof, le Français et le mélange des deux.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {["Wolof", "Français", "Wolof + Français"].map((l, i) => (
            <span key={l} className={i === 2 ? "badge-info" : "badge-muted"}>
              <IconLanguage className="h-3 w-3" aria-hidden="true" />
              {l}
            </span>
          ))}
        </div>
      </div>
      <div className="card mt-4">
        <h2 className="font-semibold text-ink">Sécurité</h2>
        <p className="mt-1 text-sm text-muted">
          Authentification à deux facteurs (TOTP) disponible via l'API. Journal d'audit actif sur
          chaque accès au dossier.
        </p>
        <button
          className="btn-secondary mt-3"
          onClick={() =>
            toast.push({
              title: "Configuration MFA",
              body: "L'activation TOTP se fait via l'API sécurisée.",
              tone: "info",
            })
          }
        >
          Configurer la MFA
        </button>
      </div>
      <div className="card mt-4">
        <h2 className="font-semibold text-ink">Fonctionnalité en préparation</h2>
        <p className="mt-1 text-sm text-muted">
          Notifications WhatsApp, langues nationales supplémentaires et préférences avancées seront
          ajoutées. Ces fonctions ne sont pas encore actives.
        </p>
        <p className="mt-3 flex items-center gap-1.5 text-xs text-muted">
          <IconExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          Aucune intégration externe n'est simulée.
        </p>
      </div>
    </div>
  );
}
