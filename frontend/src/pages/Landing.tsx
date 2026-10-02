import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";
import { useMeta } from "../lib/useMeta";
import {
  IconScribe,
  IconLanguage,
  IconTeleconsultation,
  IconPatients,
  IconCoordination,
  IconSecurity,
  IconAI,
  IconCheckCircle,
  IconWarning,
  IconOffline,
  IconShieldAlert,
  IconVitals,
  IconMedication,
  IconMic,
  IconArrowRight,
  IconMenu,
  IconClose,
  IconCheck,
  IconStructure,
} from "../components/icons";
import { useState } from "react";

// Les ancres internes doivent rester valides en routage par hash (GitHub Pages) :
// on n'utilise donc pas de href="#..." brut, qui écraserait la route courante.
function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

const FEATURES = [
  {
    Icon: IconScribe,
    title: "Scribe clinique",
    body: "Parlez, le système transcrit et structure la note. Le professionnel vérifie et valide.",
  },
  {
    Icon: IconLanguage,
    title: "Wolof + Français",
    body: "Architecture multilingue pensée pour le Sénégal, avec gestion naturelle du mélange des langues.",
  },
  {
    Icon: IconTeleconsultation,
    title: "Téléconsultation",
    body: "Rendez-vous, demande, acceptation, compte rendu. Vidéo prête à connecter.",
  },
  {
    Icon: IconPatients,
    title: "Dossier patient",
    body: "Antécédents, allergies, traitements, documents, consentements — avec permissions.",
  },
  {
    Icon: IconCoordination,
    title: "Coordination des soins",
    body: "Agent communautaire, infirmier, médecin, spécialiste : chaque étape traçable.",
  },
  {
    Icon: IconSecurity,
    title: "Sécurité",
    body: "RBAC par ressource, journal d'audit, accès exceptionnel encadré, chiffrement.",
  },
];

const PIPELINE = ["Parler", "Transcrire", "Structurer", "Vérifier", "Valider"];

/** Real product visual (not a marketing illustration): the Scribe pipeline. */
function ScribePreview() {
  return (
    <div className="card overflow-hidden border-slate-200 p-0 shadow-elevated">
      <div className="flex items-center justify-between border-b border-slate-100 bg-white px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary-100 text-primary">
            <IconScribe className="h-4 w-4" aria-hidden="true" />
          </span>
          <span className="text-sm font-semibold text-ink">Scribe clinique</span>
        </div>
        <span className="badge-warn">
          <IconWarning className="h-3 w-3" aria-hidden="true" />
          Mode démonstration
        </span>
      </div>

      <div className="space-y-4 p-4">
        <div className="flex items-center gap-2">
          {PIPELINE.map((s, i) => (
            <div key={s} className="flex flex-1 items-center gap-2">
              <div className="flex flex-col items-center gap-1">
                <span
                  className={`flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold ${
                    i <= 1 ? "bg-primary text-white" : "bg-slate-200 text-slate-500"
                  }`}
                >
                  {i + 1}
                </span>
                <span className="text-[10px] text-muted">{s}</span>
              </div>
              {i < PIPELINE.length - 1 && (
                <span
                  className={`h-0.5 flex-1 rounded ${i < 1 ? "bg-primary" : "bg-slate-200"}`}
                  aria-hidden="true"
                />
              )}
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3 rounded-xl bg-primary-50 px-3 py-3">
          <span className="relative flex h-10 w-10 items-center justify-center rounded-full bg-primary text-white">
            <IconMic className="h-5 w-5" aria-hidden="true" />
            <span className="absolute inset-0 animate-pulse-ring rounded-full bg-primary/40" />
          </span>
          <div className="flex-1">
            <div className="flex h-6 items-end gap-0.5" aria-hidden="true">
              {[0.5, 0.9, 0.4, 1, 0.6, 0.85, 0.35, 0.75, 0.5, 0.95, 0.45, 0.7].map((h, i) => (
                <span
                  key={i}
                  className="w-1 animate-wave rounded-full bg-accent"
                  style={{ height: `${h * 100}%`, animationDelay: `${i * 70}ms` }}
                />
              ))}
            </div>
            <p className="mt-0.5 text-xs font-medium text-primary-800">
              Enregistrement — 00:42
            </p>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <div className="flex items-center justify-between">
            <span className="section-title">Transcription</span>
            <span className="badge-info">
              <IconLanguage className="h-3 w-3" aria-hidden="true" />
              Wolof + Français
            </span>
          </div>
          <p className="mt-2 text-sm text-ink">
            « Patient bi dafa am douleur ci ventre bi depuis trois days, te fièvre du. »
          </p>
        </div>

        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
          <div className="flex items-center gap-2">
            <span className="badge-warn">BROUILLON IA</span>
            <span className="text-xs text-amber-800">À vérifier avant validation</span>
          </div>
          <dl className="mt-2 grid grid-cols-2 gap-2 text-xs">
            <div>
              <dt className="text-muted">Motif</dt>
              <dd className="font-medium text-ink">Douleur abdominale</dd>
            </div>
            <div>
              <dt className="text-muted">Diagnostic</dt>
              <dd className="text-muted">Non documenté</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}

const HONESTY = [
  { Icon: IconCheckCircle, cls: "text-emerald-600", label: "RÉEL", note: "Fonctionne et est testé" },
  { Icon: IconWarning, cls: "text-amber-600", label: "DÉMO", note: "Données synthétiques" },
  { Icon: IconAI, cls: "text-sky-600", label: "PARTIEL", note: "Nécessite configuration" },
  { Icon: IconOffline, cls: "text-slate-500", label: "NON CONNECTÉ", note: "Service externe absent" },
  { Icon: IconShieldAlert, cls: "text-violet-600", label: "À VALIDER", note: "Validation requise" },
];

export function Landing() {
  const { meta } = useMeta();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-hero">
      <button
        type="button"
        onClick={() => scrollToId("main")}
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2"
      >
        Aller au contenu principal
      </button>

      <nav className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <Logo />
          <div className="hidden items-center gap-7 md:flex">
            <button
              type="button"
              onClick={() => scrollToId("features")}
              className="text-sm font-medium text-muted hover:text-primary"
            >
              Fonctionnalités
            </button>
            <button
              type="button"
              onClick={() => scrollToId("pipeline")}
              className="text-sm font-medium text-muted hover:text-primary"
            >
              Scribe
            </button>
            <button
              type="button"
              onClick={() => scrollToId("pricing")}
              className="text-sm font-medium text-muted hover:text-primary"
            >
              Tarifs
            </button>
            <Link to="/status" className="text-sm font-medium text-muted hover:text-primary">
              Transparence
            </Link>
            <Link to="/login" className="btn-secondary">
              Connexion
            </Link>
            <Link to="/register" className="btn-primary">
              Créer mon compte
            </Link>
          </div>
          <div className="flex items-center gap-2 md:hidden">
            <Link to="/register" className="btn-primary px-3">
              Créer
            </Link>
            <button
              className="btn-ghost px-2"
              aria-expanded={menuOpen}
              aria-controls="landing-menu"
              onClick={() => setMenuOpen((v) => !v)}
            >
              {menuOpen ? (
                <IconClose className="h-5 w-5" aria-hidden="true" />
              ) : (
                <IconMenu className="h-5 w-5" aria-hidden="true" />
              )}
              <span className="sr-only">Menu</span>
            </button>
          </div>
        </div>
        {menuOpen && (
          <div id="landing-menu" className="border-t border-slate-200 bg-white px-4 py-3 md:hidden">
            <ul className="space-y-1">
              {[
                ["features", "Fonctionnalités"],
                ["pipeline", "Scribe"],
                ["pricing", "Tarifs"],
              ].map(([id, label]) => (
                <li key={id}>
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      scrollToId(id);
                    }}
                    className="w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-ink hover:bg-primary-50"
                  >
                    {label}
                  </button>
                </li>
              ))}
              <li>
                <Link
                  to="/login"
                  className="block rounded-lg px-3 py-2 text-sm font-medium text-ink hover:bg-primary-50"
                >
                  Connexion
                </Link>
              </li>
            </ul>
          </div>
        )}
      </nav>

      {meta?.demo_banner && (
        <div className="mx-auto max-w-7xl px-4 pt-4">
          <div className="flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
            <IconWarning className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <p>
              <strong>Mode démonstration</strong> — les fonctions d'IA utilisent des données
              synthétiques. Aucun service réel n'est connecté.
            </p>
          </div>
        </div>
      )}

      <main id="main">
        {/* ---------------------------------- Hero ---------------------------------- */}
        <header className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-14 lg:grid-cols-2 lg:py-20">
          <div className="animate-fade-in-up">
            <span className="inline-flex items-center gap-2 rounded-full border border-primary-200 bg-white px-3 py-1 text-xs font-semibold text-primary-800">
              <IconAI className="h-3.5 w-3.5" aria-hidden="true" />
              Copilote clinique — Wolof &amp; Français
            </span>
            <h1 className="mt-5 text-4xl font-extrabold leading-[1.1] tracking-tight text-ink text-balance md:text-6xl">
              SunuDoctor
              <span className="mt-3 block text-2xl font-bold text-primary md:text-3xl">
                La santé connectée, au service de tous.
              </span>
            </h1>
            <p className="mt-5 max-w-xl text-lg text-muted">
              Un copilote numérique pour documenter, coordonner et faciliter les soins.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link to="/register" className="btn-primary px-6 py-3 text-base">
                Créer mon compte
                <IconArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <button
                type="button"
                onClick={() => scrollToId("pipeline")}
                className="btn-secondary px-6 py-3 text-base"
              >
                Découvrir SunuDoctor
              </button>
            </div>
            <ul className="mt-7 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted">
              {["Zéro donnée inventée", "Vérification humaine", "Traçabilité"].map((t) => (
                <li key={t} className="flex items-center gap-1.5">
                  <IconCheck className="h-4 w-4 text-emerald-600" aria-hidden="true" />
                  {t}
                </li>
              ))}
            </ul>
          </div>

          <div className="animate-fade-in-up lg:pl-6">
            <ScribePreview />
          </div>
        </header>

        {/* -------------------------------- Pipeline -------------------------------- */}
        <section id="pipeline" className="mx-auto max-w-7xl px-4 py-14">
          <div className="card bg-white p-6 sm:p-8">
            <h2 className="text-xl font-bold text-ink sm:text-2xl">Le cœur du produit</h2>
            <p className="mt-1 text-sm text-muted">
              Une note générée par l'IA reste un brouillon tant qu'un professionnel ne l'a pas
              validée.
            </p>
            <ol className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              {PIPELINE.map((step, i) => (
                <li key={step} className="flex flex-1 items-center gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary-100 text-sm font-bold text-primary-800">
                    {i + 1}
                  </span>
                  <span className="text-sm font-semibold text-ink">{step}</span>
                  {i < PIPELINE.length - 1 && (
                    <IconArrowRight
                      className="hidden h-4 w-4 shrink-0 text-slate-300 sm:block"
                      aria-hidden="true"
                    />
                  )}
                </li>
              ))}
            </ol>
            <p className="mt-5 rounded-xl bg-surface px-4 py-3 text-sm text-muted">
              L'IA n'invente jamais : information absente = « Non documenté », incertitude =
              « À vérifier ». Le diagnostic reste saisi par le professionnel.
            </p>
          </div>
        </section>

        {/* -------------------------------- Features -------------------------------- */}
        <section id="features" className="mx-auto max-w-7xl px-4 py-14">
          <h2 className="text-center text-2xl font-bold text-ink md:text-3xl">
            Ce que fait SunuDoctor
          </h2>
          <p className="mx-auto mt-2 max-w-2xl text-center text-sm text-muted">
            De la parole au dossier structuré, pour les professionnels, les structures et les
            patients.
          </p>
          <div className="mt-9 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ Icon, title, body }) => (
              <article key={title} className="card card-hover">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-50 text-primary">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="mt-4 font-semibold text-ink">{title}</h3>
                <p className="mt-1.5 text-sm text-muted">{body}</p>
              </article>
            ))}
          </div>
        </section>

        {/* ------------------------- For whom / coordination ------------------------ */}
        <section className="mx-auto max-w-7xl px-4 py-14">
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="card">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-50 text-primary">
                <IconStructure className="h-5 w-5" aria-hidden="true" />
              </span>
              <h3 className="mt-4 font-semibold text-ink">Professionnels &amp; structures</h3>
              <p className="mt-1.5 text-sm text-muted">
                Médecins, infirmiers, sages-femmes, cabinets et cliniques : documentation,
                coordination et suivi.
              </p>
            </div>
            <div className="card">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                <IconVitals className="h-5 w-5" aria-hidden="true" />
              </span>
              <h3 className="mt-4 font-semibold text-ink">Santé communautaire</h3>
              <p className="mt-1.5 text-sm text-muted">
                Agents communautaires et relais : interface simplifiée et faible connectivité.
              </p>
            </div>
            <div className="card">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-sky-50 text-sky-700">
                <IconMedication className="h-5 w-5" aria-hidden="true" />
              </span>
              <h3 className="mt-4 font-semibold text-ink">Patients</h3>
              <p className="mt-1.5 text-sm text-muted">
                Rendez-vous, documents, téléconsultations et consentements, en langage simple.
              </p>
            </div>
          </div>
        </section>

        {/* -------------------------------- Pricing -------------------------------- */}
        <section id="pricing" className="mx-auto max-w-7xl px-4 py-14">
          <div className="card bg-white">
            <h2 className="text-center text-2xl font-bold text-ink md:text-3xl">
              Tarifs de lancement
            </h2>
            <p className="mx-auto mt-2 max-w-2xl text-center text-sm text-muted">
              Tarifs de lancement indicatifs. Ne correspondent pas à une étude de marché officielle.
              Modifiables dans la configuration.
            </p>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              {[
                ["Médecin", "15 000 FCFA", "/mois"],
                ["Infirmier · Sage-femme", "10 000 FCFA", "/mois"],
                ["Agent communautaire", "5 000 FCFA", "/mois"],
              ].map(([label, price, per]) => (
                <div key={label} className="rounded-xl border border-slate-200 bg-surface p-4">
                  <p className="text-sm font-medium text-muted">{label}</p>
                  <p className="mt-1 text-xl font-bold text-primary">
                    {price}
                    <span className="text-sm font-normal text-muted">{per}</span>
                  </p>
                </div>
              ))}
            </div>
            <div className="mt-5 text-center">
              <Link to="/app/billing" className="btn-secondary">
                Voir tous les tarifs
              </Link>
            </div>
          </div>
        </section>

        {/* ------------------------------- Honesty --------------------------------- */}
        <section className="mx-auto max-w-7xl px-4 py-14">
          <div className="card border-slate-200 bg-white">
            <h2 className="text-lg font-bold text-ink">Transparence assumée</h2>
            <p className="mt-2 max-w-3xl text-sm text-muted">
              Chaque fonctionnalité affiche son statut réel. La beauté de l'interface ne masque
              jamais ce qui est réellement connecté.
            </p>
            <ul className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {HONESTY.map(({ Icon, cls, label, note }) => (
                <li key={label} className="rounded-xl border border-slate-200 p-3">
                  <Icon className={`h-5 w-5 ${cls}`} aria-hidden="true" />
                  <p className="mt-2 text-sm font-semibold text-ink">{label}</p>
                  <p className="text-xs text-muted">{note}</p>
                </li>
              ))}
            </ul>
            <Link to="/status" className="btn-secondary mt-5">
              Voir l'état des fonctionnalités
            </Link>
          </div>
        </section>

        {/* --------------------------------- CTA ----------------------------------- */}
        <section className="mx-auto max-w-7xl px-4 pb-16">
          <div className="overflow-hidden rounded-3xl bg-primary-800 px-6 py-12 text-center shadow-elevated sm:px-12">
            <h2 className="text-2xl font-bold text-white sm:text-3xl">
              Documentez mieux, coordonnez plus vite.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-primary-100">
              Créez votre espace et découvrez le Scribe clinique pensé pour le contexte sénégalais.
            </p>
            <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
              <Link
                to="/register"
                className="btn bg-white px-6 py-3 text-base text-primary-800 hover:bg-primary-50"
              >
                Créer mon compte
              </Link>
              <Link
                to="/status"
                className="btn border border-white/40 px-6 py-3 text-base text-white hover:bg-white/10"
              >
                État des fonctionnalités
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white py-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center gap-3 px-4 text-center text-sm text-muted sm:flex-row sm:justify-between sm:text-left">
          <Logo size={28} />
          <p>
            © {new Date().getFullYear()} SunuDoctor — Dakar, Sénégal. Plateforme de démonstration
            technique : aucune donnée médicale réelle n'est hébergée.
          </p>
        </div>
      </footer>
    </div>
  );
}
