import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Patient } from "../lib/api";
import {
  Avatar,
  EmptyState,
  ErrorState,
  ListSkeleton,
  PageHeader,
  useToast,
} from "../components/ui";
import { IconAdd, IconPatients, IconSearch, IconChevronRight } from "../components/icons";

type FilterKey = "all" | "demo" | "recent";

export function Patients() {
  const [patients, setPatients] = useState<Patient[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");
  const [form, setForm] = useState({ first_name: "", last_name: "", region: "", phone: "" });
  const toast = useToast();

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
    setBusy(true);
    try {
      await api.post("/patients", form);
      setForm({ first_name: "", last_name: "", region: "", phone: "" });
      setShowForm(false);
      toast.push({ title: "Dossier patient créé", tone: "success" });
      load();
    } catch (err) {
      toast.push({
        title: "Création impossible",
        body: err instanceof Error ? err.message : undefined,
        tone: "error",
      });
    } finally {
      setBusy(false);
    }
  }

  const visible = useMemo(() => {
    const list = patients ?? [];
    const q = query.trim().toLowerCase();
    return list.filter((p) => {
      if (filter === "demo" && !p.is_demo) return false;
      if (!q) return true;
      return `${p.first_name} ${p.last_name} ${p.region ?? ""} ${p.phone ?? ""}`
        .toLowerCase()
        .includes(q);
    });
  }, [patients, query, filter]);

  const FILTERS: Array<{ key: FilterKey; label: string }> = [
    { key: "all", label: "Tous" },
    { key: "demo", label: "Démo" },
    { key: "recent", label: "Récents" },
  ];

  return (
    <div>
      <PageHeader
        title="Patients"
        subtitle="Vous ne voyez que les dossiers pour lesquels vous avez une autorisation explicite."
        icon={<IconPatients className="h-5 w-5" aria-hidden="true" />}
        actions={
          <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
            <IconAdd className="h-4 w-4" aria-hidden="true" />
            Nouveau patient
          </button>
        }
      />

      {showForm && (
        <form className="card mb-5 grid gap-4 sm:grid-cols-2" onSubmit={create}>
          <div className="sm:col-span-2">
            <h2 className="font-semibold text-ink">Nouveau dossier patient</h2>
            <p className="mt-1 text-sm text-muted">
              Créez uniquement des dossiers réels. Pour une démonstration, préfixez le nom par
              « DEMO — ».
            </p>
          </div>
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
          <div className="flex gap-2 sm:col-span-2">
            <button className="btn-primary" type="submit" disabled={busy}>
              {busy ? "Création…" : "Créer le dossier"}
            </button>
            <button type="button" className="btn-ghost" onClick={() => setShowForm(false)}>
              Annuler
            </button>
          </div>
        </form>
      )}

      {/* Search + filters */}
      {(patients === null || patients.length > 0) && (
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <IconSearch
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
              aria-hidden="true"
            />
            <input
              className="input pl-9"
              type="search"
              placeholder="Rechercher un patient (nom, région, téléphone)…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Rechercher un patient"
            />
          </div>
          <div className="flex gap-1.5" role="group" aria-label="Filtres">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setFilter(f.key)}
                aria-pressed={filter === f.key}
                className={`rounded-xl px-3 py-2 text-sm font-medium transition-colors ${
                  filter === f.key
                    ? "bg-primary text-white"
                    : "border border-slate-200 bg-white text-muted hover:text-ink"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && <ErrorState message={error} onRetry={load} />}
      {!error && patients === null && <ListSkeleton rows={4} />}
      {!error && patients?.length === 0 && (
        <EmptyState
          icon={<IconPatients className="h-6 w-6" aria-hidden="true" />}
          title="Aucun patient pour le moment"
          hint="Commencez par créer votre premier dossier patient."
          action={
            <button className="btn-primary" onClick={() => setShowForm(true)}>
              <IconAdd className="h-4 w-4" aria-hidden="true" />
              Nouveau patient
            </button>
          }
        />
      )}
      {!error && patients && patients.length > 0 && visible.length === 0 && (
        <EmptyState
          icon={<IconSearch className="h-6 w-6" aria-hidden="true" />}
          title="Aucun résultat"
          hint="Aucun dossier ne correspond à votre recherche."
        />
      )}
      {!error && visible.length > 0 && (
        <ul className="space-y-2.5">
          {visible.map((p) => (
            <li key={p.id}>
              <Link
                to={`/app/patients/${p.id}`}
                className="card card-hover flex items-center gap-4 p-4"
              >
                <Avatar name={`${p.first_name} ${p.last_name}`} size={44} />
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 font-semibold text-ink">
                    <span className="truncate">
                      {p.first_name} {p.last_name}
                    </span>
                    {p.is_demo && <span className="badge-demo shrink-0">DEMO</span>}
                  </p>
                  <p className="truncate text-sm text-muted">
                    {[p.region, p.phone].filter(Boolean).join(" · ") ||
                      "Informations non documentées"}
                  </p>
                </div>
                <span className="hidden text-xs text-muted sm:block">
                  {p.date_of_birth
                    ? new Date(p.date_of_birth).toLocaleDateString("fr-FR")
                    : "Naissance non documentée"}
                </span>
                <IconChevronRight className="h-4 w-4 shrink-0 text-slate-300" aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
