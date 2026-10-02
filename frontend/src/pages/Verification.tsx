import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Facility, MyVerification, QueueEntry } from "../lib/api";
import { useAuth } from "../lib/auth";
import {
  EmptyState,
  ErrorState,
  PageHeader,
  Spinner,
  VerificationBadgePill,
} from "../components/ui";
import { IconCheck, IconClose, IconInfo, IconWarning } from "../components/icons";

function useGet<T>(path: string, nonce = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setData(null);
    setError(null);
    api
      .get<T>(path)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, [path, nonce]);
  return { data, error };
}

function useFacilitySearch(query: string, region: string, nonce = 0) {
  const [results, setResults] = useState<Facility[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (region) params.set("region", region);
    setLoading(true);
    api
      .get<{ results: Facility[] }>(`/registry/facilities?${params.toString()}`)
      .then((r) => setResults(r.results))
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [query, region, nonce]);
  return { results, loading };
}

/* ------------------------------------------------ Professional: my status */

export function MyVerification() {
  const { user } = useAuth();
  const [nonce, setNonce] = useState(0);
  const { data, error } = useGet<MyVerification>("/verification/me", nonce);

  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("");
  const { results, loading } = useFacilitySearch(query, region);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionOk, setActionOk] = useState<string | null>(null);

  const [docKind, setDocKind] = useState("license");
  const [docRef, setDocRef] = useState("");

  async function submitIdentity(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setActionError(null);
    setActionOk(null);
    try {
      await api.post("/verification/identity", {
        documents: [{ kind: docKind, reference: docRef }],
      });
      setActionOk("Justificatifs enregistrés. Vérification en cours.");
      setDocRef("");
      setNonce((n) => n + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Envoi impossible");
    } finally {
      setBusy(false);
    }
  }

  async function requestAffiliation(facility: Facility) {
    setBusy(true);
    setActionError(null);
    setActionOk(null);
    try {
      const r = await api.post<{ notice: string }>("/verification/affiliations", {
        facility_id: facility.id,
      });
      setActionOk(r.notice);
      setNonce((n) => n + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Demande impossible");
    } finally {
      setBusy(false);
    }
  }

  const isProfessional = user?.professional != null;

  return (
    <div>
      <PageHeader
        title="Vérification professionnelle"
        subtitle="La vérification n'est jamais attribuée automatiquement. Chaque étape est tracée."
      />
      {error && <ErrorState message={error} />}
      {!data && !error && <Spinner />}

      {data && (
        <div className="space-y-4">
          <section className="card">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold text-ink">Statut actuel</h2>
              <VerificationBadgePill badge={data.badge} />
            </div>
            <p className="mt-2 text-sm text-muted">{data.message}</p>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-muted">Niveau</dt>
                <dd className="font-medium text-ink">{data.level_label}</dd>
              </div>
              <div>
                <dt className="text-muted">Accès</dt>
                <dd className="font-medium text-ink">{data.access_tier}</dd>
              </div>
              <div>
                <dt className="text-muted">Documentation clinique</dt>
                <dd className="font-medium text-ink">
                  {data.can_author_clinical ? "Autorisée" : "Non autorisée"}
                </dd>
              </div>
            </dl>
            {data.review_notes && (
              <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-700">
                Note du vérificateur : {data.review_notes}
              </p>
            )}
          </section>

          {actionOk && (
            <p className="flex items-start gap-2 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800" role="status">
              <IconCheck className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              {actionOk}
            </p>
          )}
          {actionError && (
            <p className="flex items-start gap-2 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
              <IconWarning className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              {actionError}
            </p>
          )}

          {isProfessional && (
            <section className="card">
              <h2 className="font-semibold text-ink">Pièces d'identité professionnelle</h2>
              <p className="mt-1 flex items-start gap-2 text-xs text-muted">
                <IconInfo className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                Déclarez une référence de document (numéro d'ordre, pièce). Le vérificateur examinera
                chaque pièce manuellement.
              </p>
              <form className="mt-3 space-y-3" onSubmit={submitIdentity}>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="label" htmlFor="doc-kind">
                      Type de pièce
                    </label>
                    <select
                      id="doc-kind"
                      className="input"
                      value={docKind}
                      onChange={(e) => setDocKind(e.target.value)}
                    >
                      <option value="license">Numéro d'ordre / licence</option>
                      <option value="national_id">Pièce d'identité nationale</option>
                      <option value="diploma">Diplôme</option>
                      <option value="attestation">Attestation d'exercice</option>
                    </select>
                  </div>
                  <div>
                    <label className="label" htmlFor="doc-ref">
                      Référence
                    </label>
                    <input
                      id="doc-ref"
                      className="input"
                      value={docRef}
                      onChange={(e) => setDocRef(e.target.value)}
                      required
                    />
                  </div>
                </div>
                <button className="btn-primary" disabled={busy}>
                  Soumettre pour vérification
                </button>
              </form>
            </section>
          )}

          <section className="card">
            <h2 className="font-semibold text-ink">Mes appartenances</h2>
            {data.affiliations.length === 0 ? (
              <p className="mt-2 text-sm text-muted">Aucune appartenance enregistrée.</p>
            ) : (
              <ul className="mt-2 space-y-2">
                {data.affiliations.map((a) => (
                  <li
                    key={a.id}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  >
                    <span className="text-muted">Structure {a.facility_id.slice(0, 8)}…</span>
                    <span className="badge-muted">{a.status}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {isProfessional && (
            <section className="card">
              <h2 className="font-semibold text-ink">Déclarer ma structure</h2>
              <p className="mt-1 text-xs text-muted">
                Recherchez votre structure dans le référentiel. Si elle n'apparaît pas, une demande de
                vérification est créée et devra être confirmée par une source autorisée.
              </p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <input
                  className="input"
                  placeholder="Nom de la structure"
                  aria-label="Rechercher une structure"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <input
                  className="input"
                  placeholder="Région (facultatif)"
                  aria-label="Région"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                />
              </div>
              {loading && <p className="mt-2 text-sm text-muted">Recherche…</p>}
              {!loading && results.length === 0 && (
                <p className="mt-2 text-sm text-muted">
                  Aucune structure trouvée dans le référentiel pour cette recherche.
                </p>
              )}
              <ul className="mt-3 space-y-2">
                {results.map((f) => (
                  <li
                    key={f.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2"
                  >
                    <div>
                      <p className="font-medium text-ink">{f.name}</p>
                      <p className="text-xs text-muted">
                        {f.type_label} · {f.district ?? f.region ?? "Localisation non documentée"}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={f.status === "OFFICIAL_VERIFIED" ? "badge-ok" : "badge-warn"}>
                        {f.status_label}
                      </span>
                      <button
                        className="btn-secondary"
                        onClick={() => requestAffiliation(f)}
                        disabled={busy}
                      >
                        Déclarer
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------ Officer: the queue */

export function VerificationQueue() {
  const [nonce, setNonce] = useState(0);
  const { data, error } = useGet<{ queue: QueueEntry[] }>("/verification/queue", nonce);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function decide(id: string, decision: string) {
    setBusy(id);
    setMsg(null);
    try {
      const reason = decision === "REJECT" ? window.prompt("Motif du refus :") ?? "" : undefined;
      await api.post(`/verification/queue/${id}/decision`, { decision, reason });
      setNonce((n) => n + 1);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Décision impossible");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="File de vérification"
        subtitle="Une correspondance n'est jamais une validation. Toute décision est humaine et tracée."
      />
      {error && <ErrorState message={error} />}
      {!data && !error && <Spinner />}
      {msg && (
        <p className="mb-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {msg}
        </p>
      )}
      {data?.queue.length === 0 && (
        <EmptyState title="Aucune demande en attente" hint="La file de vérification est vide." />
      )}
      <ul className="space-y-2">
        {data?.queue.map((entry) => (
          <li key={entry.professional_id} className="card">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="font-semibold text-ink">
                  {entry.full_name ?? "Professionnel"}{" "}
                  {entry.is_self && <span className="badge-muted">Vous-même</span>}
                </p>
                <p className="text-sm text-muted">
                  {entry.profession ?? "Profession non documentée"} · Licence :{" "}
                  {entry.license_number ?? "Non documenté"} · Pièces : {entry.documents_submitted}
                </p>
              </div>
              <span className="badge-info">{entry.verification_level}</span>
            </div>

            <div className="mt-2 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-700">
              <p className="font-medium">
                Correspondance : {entry.match.outcome} ({Math.round(entry.match.score * 100)}%)
              </p>
              <p className="mt-0.5">{entry.match.source_note}</p>
              {entry.match.reasons.length > 0 && (
                <ul className="mt-1 list-disc pl-4">
                  {entry.match.reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              )}
              {entry.match.requires_human_review && (
                <p className="mt-1 flex items-center gap-1 font-medium text-orange-700">
                  <IconInfo className="h-3.5 w-3.5" aria-hidden="true" />
                  Vérification humaine requise — résultat non définitif.
                </p>
              )}
            </div>

            {entry.is_self ? (
              <p className="mt-2 text-sm text-muted">
                Vous ne pouvez pas vérifier votre propre identité.
              </p>
            ) : (
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  className="btn-primary"
                  disabled={busy === entry.professional_id}
                  onClick={() => decide(entry.professional_id, "APPROVE")}
                >
                  <IconCheck className="h-4 w-4" aria-hidden="true" /> Vérifier
                </button>
                <button
                  className="btn-secondary"
                  disabled={busy === entry.professional_id}
                  onClick={() => decide(entry.professional_id, "REQUEST_MORE_INFORMATION")}
                >
                  Demander des pièces
                </button>
                <button
                  className="btn-danger"
                  disabled={busy === entry.professional_id}
                  onClick={() => decide(entry.professional_id, "REJECT")}
                >
                  <IconClose className="h-4 w-4" aria-hidden="true" /> Refuser
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
