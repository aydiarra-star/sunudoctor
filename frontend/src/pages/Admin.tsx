import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { ErrorState, PageHeader, Spinner, StatusPill } from "../components/ui";

function useGet<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api
      .get<T>(path)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, [path]);
  return { data, error };
}

interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

export function AdminUsers() {
  const { data, error } = useGet<AdminUser[]>("/admin/users");
  return (
    <div>
      <PageHeader
        title="Utilisateurs"
        subtitle="Administration technique. Aucun accès automatique aux données médicales."
      />
      {error && <ErrorState message={error} />}
      {!data && !error && <Spinner />}
      {data && (
        <ul className="space-y-2">
          {data.map((u) => (
            <li key={u.id} className="card flex items-center justify-between">
              <div>
                <p className="font-semibold text-ink">{u.full_name}</p>
                <p className="text-sm text-muted">
                  {u.email} · {u.role}
                </p>
              </div>
              <span className={u.is_active ? "badge-ok" : "badge-muted"}>
                {u.is_active ? "Actif" : "Désactivé"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface Verification {
  id: string;
  professional_id: string;
  profession: string | null;
  license_number: string | null;
  status: string;
}

export function AdminVerifications() {
  const { data, error } = useGet<Verification[]>("/admin/verifications");
  const [nonce, setNonce] = useState(0);

  async function decide(id: string, status: string) {
    await api.post(`/admin/verifications/${id}/decision`, { status });
    setNonce((n) => n + 1);
  }

  return (
    <div key={nonce}>
      <PageHeader
        title="Vérifications"
        subtitle="Le statut « Vérifié » n'est jamais attribué automatiquement."
      />
      {error && <ErrorState message={error} />}
      {!data && !error && <Spinner />}
      {data?.length === 0 && <p className="text-sm text-muted">Aucune demande en attente.</p>}
      <ul className="space-y-2">
        {data?.map((v) => (
          <li key={v.id} className="card flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="font-semibold text-ink">{v.profession ?? "Professionnel"}</p>
              <p className="text-sm text-muted">Licence : {v.license_number ?? "Non documenté"}</p>
            </div>
            <div className="flex items-center gap-2">
              <StatusPill status={v.status} />
              <button className="btn-secondary" onClick={() => decide(v.id, "in_review")}>
                En cours
              </button>
              <button className="btn-primary" onClick={() => decide(v.id, "verified")}>
                Vérifier
              </button>
              <button className="btn-danger" onClick={() => decide(v.id, "refused")}>
                Refuser
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

interface Org {
  id: string;
  name: string;
  type: string;
  region: string | null;
  city: string | null;
  is_demo: boolean;
}

export function AdminOrganizations() {
  const { data, error } = useGet<Org[]>("/admin/organizations");
  return (
    <div>
      <PageHeader title="Structures" subtitle="Organisations enregistrées." />
      {error && <ErrorState message={error} />}
      {!data && !error && <Spinner />}
      <ul className="space-y-2">
        {data?.map((o) => (
          <li key={o.id} className="card flex items-center justify-between">
            <div>
              <p className="font-semibold text-ink">
                {o.name} {o.is_demo && <span className="badge-demo ml-1">DEMO</span>}
              </p>
              <p className="text-sm text-muted">
                {o.type} · {[o.city, o.region].filter(Boolean).join(", ") || "Localisation non documentée"}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

interface Subscription {
  id: string;
  plan_code: string;
  price_fcfa: number;
  status: string;
}

export function AdminSubscriptions() {
  const { data, error } = useGet<Subscription[]>("/admin/subscriptions");
  return (
    <div>
      <PageHeader title="Abonnements" subtitle="Données de facturation, séparées des données cliniques." />
      {error && <ErrorState message={error} />}
      {!data && !error && <Spinner />}
      <ul className="space-y-2">
        {data?.map((s) => (
          <li key={s.id} className="card flex items-center justify-between">
            <span className="text-ink">
              {s.plan_code} — {s.price_fcfa.toLocaleString("fr-FR")} FCFA
            </span>
            <StatusPill status={s.status} />
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AdminPayments() {
  return (
    <div>
      <PageHeader title="Paiements" subtitle="Suivi des transactions." />
      <div className="card">
        <p className="text-sm text-muted">
          Aucun paiement réel n'est traité en mode démonstration. Les fournisseurs (Wave, Orange
          Money, carte, virement) nécessitent une configuration côté serveur.
        </p>
      </div>
    </div>
  );
}

interface AuditEntry {
  id: string;
  actor_id: string | null;
  actor_role: string | null;
  action: string;
  resource_type: string | null;
  patient_id: string | null;
  created_at: string;
}

export function AdminAudit() {
  const { data, error } = useGet<AuditEntry[]>("/admin/audit?limit=100");
  return (
    <div>
      <PageHeader title="Audit" subtitle="Journal des actions sensibles." />
      {error && <ErrorState message={error} />}
      {!data && !error && <Spinner />}
      {data?.length === 0 && <p className="text-sm text-muted">Aucune entrée d'audit.</p>}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[40rem] text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase text-muted">
              <th className="py-2 pr-4">Action</th>
              <th className="py-2 pr-4">Rôle</th>
              <th className="py-2 pr-4">Ressource</th>
              <th className="py-2">Date</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((l) => (
              <tr key={l.id} className="border-b border-slate-100">
                <td className="py-2 pr-4 font-medium text-ink">{l.action}</td>
                <td className="py-2 pr-4 text-muted">{l.actor_role ?? "—"}</td>
                <td className="py-2 pr-4 text-muted">{l.resource_type ?? "—"}</td>
                <td className="py-2 text-muted">{new Date(l.created_at).toLocaleString("fr-FR")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface SecuritySummary {
  audit_entries: number;
  break_glass_events: number;
  failed_logins: number;
  separation_of_duties: boolean;
  notice: string;
}

export function AdminSecurity() {
  const { data, error } = useGet<SecuritySummary>("/admin/security/summary");
  return (
    <div>
      <PageHeader title="Sécurité" subtitle="Vue d'ensemble, sans contenu clinique." />
      {error && <ErrorState message={error} />}
      {!data && !error && <Spinner />}
      {data && (
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="card">
            <p className="text-3xl font-bold text-primary">{data.audit_entries}</p>
            <p className="text-sm text-muted">Entrées d'audit</p>
          </div>
          <div className="card">
            <p className="text-3xl font-bold text-primary">{data.break_glass_events}</p>
            <p className="text-sm text-muted">Accès exceptionnels</p>
          </div>
          <div className="card">
            <p className="text-3xl font-bold text-primary">{data.failed_logins}</p>
            <p className="text-sm text-muted">Connexions échouées</p>
          </div>
          <div className="card sm:col-span-3">
            <p className="text-sm text-muted">{data.notice}</p>
          </div>
        </div>
      )}
    </div>
  );
}

interface PlatformConfig {
  environment: string;
  ai_mode: string;
  payment_mode: string;
  trial_days: number;
  secrets_exposed: boolean;
}

export function AdminConfig() {
  const { data, error } = useGet<PlatformConfig>("/admin/config");
  return (
    <div>
      <PageHeader title="Configuration" subtitle="Configuration non secrète de la plateforme." />
      {error && <ErrorState message={error} />}
      {!data && !error && <Spinner />}
      {data && (
        <div className="card">
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase text-muted">Environnement</dt>
              <dd className="text-sm text-ink">{data.environment}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-muted">Mode IA</dt>
              <dd className="text-sm text-ink">{data.ai_mode}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-muted">Mode paiement</dt>
              <dd className="text-sm text-ink">{data.payment_mode}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-muted">Essai</dt>
              <dd className="text-sm text-ink">{data.trial_days} jours</dd>
            </div>
          </dl>
          <p className="mt-3 text-xs text-muted">
            Secrets exposés : {data.secrets_exposed ? "oui" : "non"} — aucun secret n'est renvoyé par
            l'API.
          </p>
        </div>
      )}
    </div>
  );
}

export function AdminSupport() {
  return (
    <div>
      <PageHeader title="Support" subtitle="Assistance et signalements." />
      <div className="card">
        <h2 className="font-semibold text-ink">Fonctionnalité en préparation</h2>
        <p className="mt-1 text-sm text-muted">
          Le centre de support (tickets, suivi, base de connaissances) n'est pas encore actif.
        </p>
      </div>
    </div>
  );
}
