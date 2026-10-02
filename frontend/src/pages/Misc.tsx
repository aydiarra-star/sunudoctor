import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { EmptyState, ErrorState, PageHeader, Spinner } from "../components/ui";

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

/** Simple, honest list page used by several sections. */
function ListPage<T>({
  title,
  subtitle,
  path,
  empty,
  render,
  notice,
}: {
  title: string;
  subtitle: string;
  path: string;
  empty: string;
  render: (item: T) => React.ReactNode;
  notice?: string;
}) {
  const { data, error, reload } = useList<T>(path);
  return (
    <div>
      <PageHeader title={title} subtitle={subtitle} />
      {notice && (
        <p className="mb-4 rounded-xl border border-slate-300 bg-slate-50 px-4 py-2 text-sm text-muted">
          {notice}
        </p>
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {!error && data === null && <Spinner />}
      {!error && data?.length === 0 && <EmptyState title={empty} />}
      {!error && data && data.length > 0 && (
        <ul className="space-y-2">
          {data.map((item, i) => (
            <li key={i} className="card">
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
      path="/messages"
      empty="Aucun message"
      notice="Les messages sont limités aux personnes autorisées sur le dossier concerné."
      render={(m) => (
        <div>
          <p className="text-sm text-ink">{m.body}</p>
          <p className="mt-1 text-xs text-muted">
            {new Date(m.created_at).toLocaleString("fr-FR")} · {m.read ? "Lu" : "Non lu"}
          </p>
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
      path="/documents"
      empty="Aucun document"
      render={(d) => (
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold text-ink">
              {d.title} {d.is_demo && <span className="badge-demo ml-1">DEMO</span>}
            </p>
            <p className="text-sm text-muted">
              {d.doc_type} · version {d.version}
            </p>
          </div>
          <span className="badge-muted">{d.status}</span>
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
      path="/referrals"
      empty="Aucune orientation"
      notice="Chaque étape est traçable et auditée."
      render={(r) => (
        <div>
          <p className="font-semibold text-ink">{r.reason}</p>
          <p className="text-sm text-muted">
            Priorité {r.priority} · {new Date(r.created_at).toLocaleString("fr-FR")}
          </p>
          <span className="badge-info mt-1">{r.status}</span>
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
      path="/appointments"
      empty="Aucun rendez-vous"
      render={(a) => (
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold text-ink">
              {new Date(a.scheduled_at).toLocaleString("fr-FR")}
            </p>
            <p className="text-sm text-muted">
              {a.channel === "teleconsultation" ? "Téléconsultation" : "Présentiel"}
              {a.reason ? ` · ${a.reason}` : ""}
            </p>
          </div>
          <span className="badge-info">{a.status}</span>
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
    <ListPage<TeleItem>
      title="Téléconsultation"
      subtitle="Rendez-vous, demande, acceptation, vidéo, audio, chat, documents, compte rendu."
      path="/teleconsultations"
      empty="Aucune téléconsultation"
      notice="Vidéo — configuration requise. Aucun service vidéo réel (WebRTC/ICE) n'est connecté."
      render={(t) => (
        <div className="flex items-center justify-between">
          <div>
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
  const [reload] = useState(0);

  useEffect(() => {
    if (!patientId) return;
    api
      .get<ConsentItem[]>(`/consents?patient_id=${patientId}`)
      .then(setConsents)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, [patientId, reload]);

  return (
    <div>
      <PageHeader
        title="Mes consentements"
        subtitle="Accès, partage, téléconsultation, audio, IA, recherche."
      />
      {!patientId && (
        <EmptyState
          title="Sélectionnez un dossier patient"
          hint="Les consentements sont rattachés à un dossier patient."
        />
      )}
      {error && <ErrorState message={error} />}
      {patientId && consents?.length === 0 && <EmptyState title="Aucun consentement enregistré" />}
      {consents && consents.length > 0 && (
        <ul className="space-y-2">
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

  return (
    <div>
      <PageHeader title="Profil" subtitle="Vos informations et votre statut de vérification." />
      {error && <ErrorState message={error} />}
      {!error && me === null && <Spinner />}
      {me && (
        <div className="card">
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold uppercase text-muted">Nom</dt>
              <dd className="text-sm text-ink">{String(me.full_name ?? "")}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-muted">E-mail</dt>
              <dd className="text-sm text-ink">{String(me.email ?? "")}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-muted">Rôle</dt>
              <dd className="text-sm text-ink">{String(me.role ?? "")}</dd>
            </div>
            {prof && (
              <div>
                <dt className="text-xs font-semibold uppercase text-muted">Vérification</dt>
                <dd className="text-sm text-ink">{prof.verification_status}</dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </div>
  );
}

export function Settings() {
  return (
    <div>
      <PageHeader title="Paramètres" subtitle="Préférences du compte et sécurité." />
      <div className="card">
        <h2 className="font-semibold text-ink">Sécurité</h2>
        <p className="mt-1 text-sm text-muted">
          Authentification à deux facteurs (TOTP) disponible via l'API. Configuration depuis le
          profil sécurisé.
        </p>
      </div>
      <div className="card mt-4">
        <h2 className="font-semibold text-ink">Fonctionnalité en préparation</h2>
        <p className="mt-1 text-sm text-muted">
          Notifications WhatsApp, langues nationales supplémentaires et préférences avancées seront
          ajoutées. Ces fonctions ne sont pas encore actives.
        </p>
      </div>
    </div>
  );
}
