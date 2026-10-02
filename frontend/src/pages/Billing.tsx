import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { ErrorState, PageHeader, Spinner } from "../components/ui";

interface Plan {
  code: string;
  label: string;
  price_fcfa: number;
  category: string;
}
interface PlansResponse {
  label: string;
  disclaimer: string;
  trial_days: number;
  plans: Plan[];
}
interface Provider {
  code: string;
  label: string;
  connected: boolean;
}
interface ProvidersResponse {
  mode: string;
  providers: Provider[];
  notice: string;
}

export function Billing() {
  const [plans, setPlans] = useState<PlansResponse | null>(null);
  const [providers, setProviders] = useState<ProvidersResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sub, setSub] = useState<{ id: string } | null>(null);
  const [payment, setPayment] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<PlansResponse>("/billing/plans"),
      api.get<ProvidersResponse>("/billing/providers"),
    ])
      .then(([p, pr]) => {
        setPlans(p);
        setProviders(pr);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, []);

  async function subscribe(code: string) {
    try {
      const s = await api.post<{ id: string }>("/billing/subscribe", { plan_code: code });
      setSub(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  async function pay(provider: string) {
    if (!sub) return;
    try {
      const p = await api.post<Record<string, unknown>>("/billing/payments", {
        subscription_id: sub.id,
        provider,
      });
      setPayment(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  return (
    <div>
      <PageHeader title="Abonnement" subtitle="Tarifs de lancement et paiement." />
      {error && <ErrorState message={error} />}
      {!plans && !error && <Spinner />}

      {plans && (
        <>
          <div className="mb-4 rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-muted">
            <strong className="text-ink">{plans.label}</strong> — {plans.disclaimer} ·{" "}
            {plans.trial_days} jours d'essai.
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {plans.plans.map((p) => (
              <div key={p.code} className="card">
                <h3 className="font-semibold text-ink">{p.label}</h3>
                <p className="mt-1 text-lg font-bold text-primary">
                  {p.price_fcfa.toLocaleString("fr-FR")} FCFA
                  <span className="text-sm font-normal text-muted">/mois</span>
                </p>
                <button className="btn-secondary mt-3" onClick={() => subscribe(p.code)}>
                  Choisir
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      {providers && (
        <div className="card mt-6">
          <h2 className="font-semibold text-ink">Moyens de paiement</h2>
          <p className="mt-1 text-sm text-muted">{providers.notice}</p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {providers.providers.map((p) => (
              <li key={p.code}>
                <button
                  className="btn-secondary"
                  disabled={!sub}
                  onClick={() => pay(p.code)}
                  title={p.connected ? "Connecté" : "Configuration requise"}
                >
                  {p.label}
                  <span className={p.connected ? "badge-ok" : "badge-warn"}>
                    {p.connected ? "Connecté" : "Non connecté"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {sub && (
            <p className="mt-3 text-sm text-emerald-700">
              Essai activé. Sélectionnez un moyen de paiement (mode démonstration).
            </p>
          )}
          {payment && (
            <div className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
              <p className="font-semibold">Mode démonstration</p>
              <p>{String(payment.message ?? "")}</p>
              <p className="text-xs">
                Référence : {String(payment.reference ?? "")} · statut : {String(payment.status ?? "")}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
