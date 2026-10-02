import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { CardSkeleton, ErrorState, PageHeader, useToast } from "../components/ui";
import {
  IconBilling,
  IconCheck,
  IconWarning,
  IconInfo,
} from "../components/icons";

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
  const toast = useToast();

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
      toast.push({ title: "Abonnement sélectionné", body: "Essai de démonstration activé.", tone: "success" });
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
      <PageHeader
        title="Abonnement"
        subtitle="Tarifs de lancement et moyens de paiement."
        icon={<IconBilling className="h-5 w-5" aria-hidden="true" />}
      />

      {error && <ErrorState message={error} />}
      {!plans && !error && <CardSkeleton />}

      {plans && (
        <>
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-primary-200 bg-primary-50 px-4 py-3 text-sm text-primary-900">
            <IconInfo className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <div>
              <p className="font-semibold">{plans.label}</p>
              <p className="mt-0.5 text-primary-800">
                {plans.disclaimer} · {plans.trial_days} jours d'essai.
              </p>
              <p className="mt-1 text-xs text-primary-700">
                Un impayé ne modifie ni ne supprime jamais une donnée clinique (séparation
                ClinicalData / BillingData).
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {plans.plans.map((p) => (
              <div key={p.code} className="card flex flex-col">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                  {p.category}
                </p>
                <h3 className="mt-1 font-semibold text-ink">{p.label}</h3>
                <p className="mt-2 text-2xl font-bold text-primary">
                  {p.price_fcfa.toLocaleString("fr-FR")}
                  <span className="ml-1 text-sm font-normal text-muted">FCFA/mois</span>
                </p>
                <button
                  className="btn-secondary mt-4 w-full"
                  onClick={() => subscribe(p.code)}
                >
                  Choisir
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      {providers && (
        <div className="card mt-6">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-ink">Moyens de paiement</h2>
            <span className="badge-warn">
              <IconWarning className="h-3 w-3" aria-hidden="true" />
              {providers.mode === "demo" ? "Mode démonstration" : providers.mode}
            </span>
          </div>
          <p className="mt-1 text-sm text-muted">{providers.notice}</p>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {providers.providers.map((p) => (
              <li key={p.code}>
                <button
                  className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 text-left transition-colors hover:border-primary-300 disabled:opacity-60"
                  disabled={!sub}
                  onClick={() => pay(p.code)}
                  title={p.connected ? "Connecté" : "Configuration requise"}
                >
                  <span className="font-medium text-ink">{p.label}</span>
                  <span className={p.connected ? "badge-ok" : "badge-muted"}>
                    {p.connected ? (
                      <>
                        <IconCheck className="h-3 w-3" aria-hidden="true" />
                        Connecté
                      </>
                    ) : (
                      "Configuration requise"
                    )}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {!sub && (
            <p className="mt-3 text-xs text-muted">
              Sélectionnez d'abord un abonnement pour tester un moyen de paiement.
            </p>
          )}
          {sub && !payment && (
            <p className="mt-3 text-sm text-emerald-700">
              Essai activé. Sélectionnez un moyen de paiement (mode démonstration).
            </p>
          )}
          {payment && (
            <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <p className="font-semibold">Mode démonstration — aucun paiement réel</p>
              <p className="mt-0.5">{String(payment.message ?? "")}</p>
              <p className="mt-1 text-xs">
                Référence : {String(payment.reference ?? "")} · statut :{" "}
                {String(payment.status ?? "")}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
