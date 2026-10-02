import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Logo } from "../components/Logo";
import { useAuth } from "../lib/auth";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      navigate("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connexion impossible");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-10">
      <div className="mb-6 flex justify-center">
        <Link to="/">
          <Logo />
        </Link>
      </div>
      <div className="card">
        <h1 className="text-xl font-bold text-ink">Connexion</h1>
        {error && (
          <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}
        <form className="mt-5 space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="label" htmlFor="email">
              E-mail
            </label>
            <input
              id="email"
              type="email"
              className="input"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="password">
              Mot de passe
            </label>
            <input
              id="password"
              type="password"
              className="input"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? "Connexion…" : "Se connecter"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-muted">
          Pas de compte ?{" "}
          <Link to="/register" className="text-primary underline">
            Créer mon compte
          </Link>
        </p>
      </div>
    </div>
  );
}
