import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Patient } from "../lib/api";
import { EmptyState, ErrorState, PageHeader, Spinner } from "../components/ui";

export function Patients() {
  const [patients, setPatients] = useState<Patient[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ first_name: "", last_name: "", region: "", phone: "" });

  function load() {
    setError(null);
    api
      .get<Patient[]>("/patients")
      .then(setPatients)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }

  useEffect(load, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.post("/patients", form);
      setForm({ first_name: "", last_name: "", region: "", phone: "" });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Création impossible");
    }
  }

  return (
    <div>
      <PageHeader
        title="Patients"
        subtitle="Vous ne voyez que les dossiers pour lesquels vous avez une autorisation."
        actions={
          <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
            Nouveau patient
          </button>
        }
      />

      {showForm && (
        <form className="card mb-4 grid gap-3 sm:grid-cols-2" onSubmit={create}>
          <div>
            <label className="label" htmlFor="first_name">
              Prénom
            </label>
            <input
              id="first_name"
              className="input"
              required
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
            />
          </div>
          <div>
            <label className="label" htmlFor="last_name">
              Nom
            </label>
            <input
              id="last_name"
              className="input"
              required
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            />
          </div>
          <div>
            <label className="label" htmlFor="region">
              Région (facultatif)
            </label>
            <input
              id="region"
              className="input"
              value={form.region}
              onChange={(e) => setForm({ ...form, region: e.target.value })}
            />
          </div>
          <div>
            <label className="label" htmlFor="phone">
              Téléphone (facultatif)
            </label>
            <input
              id="phone"
              className="input"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>
          <div className="sm:col-span-2">
            <button className="btn-primary" type="submit">
              Créer le dossier
            </button>
          </div>
        </form>
      )}

      {error && <ErrorState message={error} onRetry={load} />}
      {!error && patients === null && <Spinner />}
      {!error && patients?.length === 0 && (
        <EmptyState
          title="Aucun patient autorisé"
          hint="Créez un dossier ou demandez une autorisation d'accès."
        />
      )}
      {!error && patients && patients.length > 0 && (
        <ul className="space-y-2">
          {patients.map((p) => (
            <li key={p.id} className="card flex items-center justify-between">
              <div>
                <p className="font-semibold text-ink">
                  {p.first_name} {p.last_name}
                  {p.is_demo && <span className="badge-demo ml-2">DEMO</span>}
                </p>
                <p className="text-sm text-muted">
                  {[p.region, p.phone].filter(Boolean).join(" · ") || "Informations non documentées"}
                </p>
              </div>
              <Link to={`/app/patients/${p.id}`} className="btn-secondary">
                Ouvrir
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
