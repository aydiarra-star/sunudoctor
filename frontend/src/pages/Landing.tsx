import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";
import { useMeta } from "../lib/useMeta";

const FEATURES = [
  {
    title: "Scribe clinique",
    body: "Parlez, le système transcrit et structure la note. Le professionnel vérifie et valide.",
  },
  {
    title: "Wolof + Français",
    body: "Architecture multilingue pensée pour le Sénégal, avec gestion du mélange des langues.",
  },
  {
    title: "Téléconsultation",
    body: "Rendez-vous, demande, acceptation, compte rendu. Vidéo prête à connecter.",
  },
  {
    title: "Dossier patient",
    body: "Antécédents, allergies, traitements, documents, consentements — avec permissions.",
  },
  {
    title: "Coordination des soins",
    body: "Agent communautaire, infirmier, médecin, spécialiste : chaque étape traçable.",
  },
  {
    title: "Santé communautaire",
    body: "Interface simplifiée et fonctionnement en faible connectivité.",
  },
  {
    title: "Sécurité",
    body: "RBAC par ressource, journal d'audit, accès exceptionnel encadré, chiffrement.",
  },
];

export function Landing() {
  const { meta } = useMeta();

  return (
    <div className="min-h-screen bg-white">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2"
      >
        Aller au contenu principal
      </a>

      <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
        <Logo />
        <div className="hidden items-center gap-6 md:flex">
          <a href="#features" className="text-sm font-medium text-muted hover:text-primary">
            Fonctionnalités
          </a>
          <a href="#pricing" className="text-sm font-medium text-muted hover:text-primary">
            Tarifs
          </a>
          <Link to="/login" className="btn-secondary">
            Connexion
          </Link>
          <Link to="/register" className="btn-primary">
            Créer mon compte
          </Link>
        </div>
        <div className="flex items-center gap-2 md:hidden">
          <Link to="/login" className="btn-secondary">
            Connexion
          </Link>
          <Link to="/register" className="btn-primary">
            Créer
          </Link>
        </div>
      </nav>

      {meta?.demo_banner && (
        <div className="mx-auto max-w-7xl px-4">
          <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
            <strong>Mode démonstration</strong> — les fonctions d'IA utilisent des données
            synthétiques. Aucun service réel n'est connecté.
          </div>
        </div>
      )}

      <main id="main">
        <header className="mx-auto max-w-7xl px-4 py-14 text-center md:py-20">
          <h1 className="text-4xl font-extrabold leading-tight text-ink md:text-6xl">
            SunuDoctor
            <span className="mt-3 block text-2xl font-bold text-primary md:text-3xl">
              La santé connectée, au service de tous.
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted">
            Un copilote numérique pour documenter, coordonner et faciliter les soins.
          </p>
          <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
            <Link to="/register" className="btn-primary px-6 py-3 text-base">
              Créer mon compte
            </Link>
            <a href="#features" className="btn-secondary px-6 py-3 text-base">
              Découvrir SunuDoctor
            </a>
          </div>
        </header>

        <section id="features" className="mx-auto max-w-7xl px-4 py-12">
          <h2 className="text-center text-2xl font-bold text-ink md:text-3xl">
            Ce que fait SunuDoctor
          </h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <article key={f.title} className="card">
                <h3 className="font-semibold text-ink">{f.title}</h3>
                <p className="mt-1.5 text-sm text-muted">{f.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-12">
          <div className="card bg-primary-light">
            <h2 className="text-xl font-bold text-primary-dark">Le cœur du produit</h2>
            <p className="mt-3 text-sm font-semibold text-ink">
              PARLER → TRANSCRIRE → STRUCTURER → VÉRIFIER → VALIDER
            </p>
            <p className="mt-2 text-sm text-muted">
              Une note générée par l'IA reste un brouillon tant qu'un professionnel ne l'a pas
              validée. L'IA n'invente jamais : information absente = « Non documenté »,
              incertitude = « À vérifier ».
            </p>
          </div>
        </section>

        <section id="pricing" className="mx-auto max-w-7xl px-4 py-12">
          <h2 className="text-center text-2xl font-bold text-ink md:text-3xl">
            Tarifs de lancement
          </h2>
          <p className="mx-auto mt-2 max-w-2xl text-center text-sm text-muted">
            Tarifs de lancement. Ne correspondent pas à une étude de marché officielle.{" "}
            <Link to="/app/billing" className="text-primary underline">
              Voir le détail
            </Link>
          </p>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-12">
          <div className="card border-slate-300">
            <h2 className="text-lg font-bold text-ink">Transparence</h2>
            <p className="mt-2 text-sm text-muted">
              Cette plateforme distingue explicitement ce qui fonctionne réellement (RÉEL), ce qui
              fonctionne avec des données synthétiques (DÉMO), ce qui nécessite une configuration
              (PARTIEL) et ce qui est prêt mais non connecté (NON CONNECTÉ).
            </p>
            <Link to="/status" className="btn-secondary mt-4">
              Voir l'état des fonctionnalités
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 py-8">
        <div className="mx-auto max-w-7xl px-4 text-center text-sm text-muted">
          <p>© {new Date().getFullYear()} SunuDoctor — Dakar, Sénégal.</p>
          <p className="mt-1">
            Plateforme de démonstration technique. Aucune donnée médicale réelle n'est hébergée.
          </p>
        </div>
      </footer>
    </div>
  );
}
