import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Logo } from "../components/Logo";
import { useAuth, type RegisterPayload } from "../lib/auth";

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

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register(form);
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
    <div className="mx-auto max-w-lg px-4 py-10">
      <div className="mb-6 flex justify-center">
        <Link to="/">
          <Logo />
        </Link>
      </div>
      <div className="card">
        <h1 className="text-xl font-bold text-ink">Créer mon compte</h1>
        <p className="mt-1 text-sm text-muted">
          Les professionnels de santé passent par une vérification. Le statut « Vérifié » n'est
          jamais attribué automatiquement.
        </p>

        {error && (
          <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}

        <form className="mt-5 space-y-4" onSubmit={onSubmit}>
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
                <label className="label" htmlFor="organization_name">
                  Structure (facultatif)
                </label>
                <input
                  id="organization_name"
                  className="input"
                  value={form.organization_name ?? ""}
                  onChange={(e) => set("organization_name", e.target.value)}
                />
              </div>
            </>
          )}
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? "Création…" : "Créer mon compte"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-muted">
          Déjà un compte ?{" "}
          <Link to="/login" className="text-primary underline">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}
