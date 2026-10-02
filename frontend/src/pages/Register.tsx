import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthShell } from "../components/AuthShell";
import { useAuth, type RegisterPayload } from "../lib/auth";
import { api, type Facility } from "../lib/api";
import { IconWarning, IconInfo } from "../components/icons";

const ROLES = [
  { value: "doctor", label: "Médecin" },
  { value: "nurse", label: "Infirmier" },
  { value: "midwife", label: "Sage-femme" },
  { value: "other_professional", label: "Autre professionnel" },
  { value: "community_agent", label: "Agent communautaire" },
  { value: "social_worker", label: "Assistant social" },
  { value: "patient", label: "Patient" },
  { value: "org_admin", label: "Administrateur de structure" },
];

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState<RegisterPayload>({
    email: "",
    password: "",
    full_name: "",
    role: "doctor",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const isProfessional = !["patient", "org_admin"].includes(form.role);

  // Facility referential search. The list only shows what the referential
  // actually holds; an empty result means the facility must be requested.
  const [facilityQuery, setFacilityQuery] = useState("");
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selected, setSelected] = useState<Facility | null>(null);
  const [requesting, setRequesting] = useState(false);

  useEffect(() => {
    if (!isProfessional) return;
    const params = new URLSearchParams();
    if (facilityQuery) params.set("q", facilityQuery);
    if (form.region) params.set("region", form.region);
    api
      .get<{ results: Facility[] }>(`/registry/facilities?${params.toString()}`)
      .then((r) => setFacilities(r.results))
      .catch(() => setFacilities([]));
  }, [facilityQuery, form.region, isProfessional]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (isProfessional && !selected && !requesting) {
      setError(
        "Sélectionnez votre structure dans le référentiel, ou demandez sa vérification si elle n'apparaît pas.",
      );
      return;
    }
    setBusy(true);
    try {
      const payload: RegisterPayload = { ...form };
      if (isProfessional) {
        if (selected) {
          payload.facility_id = selected.id;
          payload.requested_facility_name = undefined;
        } else {
          payload.requested_facility_name = facilityQuery.trim() || form.organization_name;
          payload.facility_id = undefined;
        }
      }
      await register(payload);
      navigate("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Inscription impossible");
    } finally {
      setBusy(false);
    }
  }

  function set<K extends keyof RegisterPayload>(k: K, v: RegisterPayload[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  return (
    <AuthShell>
      <h1 className="text-2xl font-bold tracking-tight text-ink">Créer mon compte</h1>
      <p className="mt-1 flex items-start gap-2 text-sm text-muted">
        <IconInfo className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
        Les professionnels de santé passent par une vérification. Le statut « Vérifié » n'est jamais
        attribué automatiquement.
      </p>

      {error && (
        <p
          className="mt-5 flex items-start gap-2 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700"
          role="alert"
        >
          <IconWarning className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}

      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <div>
          <label className="label" htmlFor="full_name">
            Nom complet
          </label>
          <input
            id="full_name"
            className="input"
            required
            value={form.full_name}
            onChange={(e) => set("full_name", e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="email">
            E-mail
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className="input"
            required
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="password">
            Mot de passe (8 caractères minimum)
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            className="input"
            required
            minLength={8}
            value={form.password}
            onChange={(e) => set("password", e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="role">
            Profil
          </label>
          <select
            id="role"
            className="input"
            value={form.role}
            onChange={(e) => set("role", e.target.value)}
          >
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
        {isProfessional && (
          <>
            <div>
              <label className="label" htmlFor="license_number">
                Numéro d'ordre / licence (facultatif)
              </label>
              <input
                id="license_number"
                className="input"
                value={form.license_number ?? ""}
                onChange={(e) => set("license_number", e.target.value)}
              />
              <p className="mt-1 text-xs text-muted">
                Sera soumis à vérification. Aucune validation automatique.
              </p>
            </div>
            <div>
              <label className="label" htmlFor="region">
                Région
              </label>
              <input
                id="region"
                className="input"
                value={form.region ?? ""}
                onChange={(e) => set("region", e.target.value)}
              />
            </div>

            <fieldset className="rounded-xl border border-slate-200 p-3">
              <legend className="px-1 text-sm font-semibold text-ink">
                Structure de santé
              </legend>
              <p className="flex items-start gap-2 text-xs text-muted">
                <IconInfo className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                Obligatoire. Choisissez votre structure dans le référentiel. Si elle n'y figure pas,
                demandez sa vérification : elle ne sera jamais considérée comme officielle
                automatiquement.
              </p>

              <input
                className="input mt-3"
                placeholder="Rechercher une structure…"
                aria-label="Rechercher une structure"
                value={facilityQuery}
                onChange={(e) => {
                  setFacilityQuery(e.target.value);
                  setSelected(null);
                }}
              />

              {selected ? (
                <div className="mt-2 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-primary-50 px-3 py-2">
                  <div>
                    <p className="font-medium text-ink">{selected.name}</p>
                    <p className="text-xs text-muted">
                      {selected.type_label} · {selected.status_label}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setSelected(null)}
                  >
                    Changer
                  </button>
                </div>
              ) : (
                <>
                  <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto">
                    {facilities.map((f) => (
                      <li key={f.id}>
                        <button
                          type="button"
                          className="w-full rounded-xl border border-slate-200 px-3 py-2 text-left text-sm hover:border-primary hover:bg-primary-50"
                          onClick={() => {
                            setSelected(f);
                            setRequesting(false);
                            setFacilityQuery(f.name);
                          }}
                        >
                          <span className="font-medium text-ink">{f.name}</span>
                          <span className="block text-xs text-muted">
                            {f.type_label} · {f.status_label}
                          </span>
                        </button>
                      </li>
                    ))}
                    {facilities.length === 0 && (
                      <li className="px-1 py-2 text-xs text-muted">
                        Aucune structure trouvée. Vous pouvez demander sa vérification ci-dessous.
                      </li>
                    )}
                  </ul>
                  <label className="mt-2 flex items-start gap-2 text-sm text-ink">
                    <input
                      type="checkbox"
                      className="mt-0.5"
                      checked={requesting}
                      onChange={(e) => setRequesting(e.target.checked)}
                    />
                    <span>
                      Ma structure n'apparaît pas — demander sa vérification
                      {facilityQuery.trim() ? ` : « ${facilityQuery.trim()} »` : ""}
                    </span>
                  </label>
                </>
              )}
            </fieldset>

            <div>
              <label className="label" htmlFor="role_function">
                Fonction dans la structure (facultatif)
              </label>
              <input
                id="role_function"
                className="input"
                value={form.role_function ?? ""}
                onChange={(e) => set("role_function", e.target.value)}
              />
            </div>
          </>
        )}
        <button type="submit" className="btn-primary w-full" disabled={busy}>
          {busy ? "Création…" : "Créer mon compte"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        Déjà un compte ?{" "}
        <Link to="/login" className="font-semibold text-primary hover:underline">
          Se connecter
        </Link>
      </p>
    </AuthShell>
  );
}
