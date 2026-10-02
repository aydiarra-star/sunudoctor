import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";
import { IconCheckCircle, IconScribe, IconLanguage, IconSecurity } from "../components/icons";

/** Shared premium split-screen shell for authentication pages. */
export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Left — form */}
      <div className="flex flex-col bg-hero px-4 py-8 sm:px-8">
        <Link to="/" className="mb-8 inline-flex">
          <Logo />
        </Link>
        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center pb-10">
          {children}
        </div>
      </div>

      {/* Right — product reassurance (desktop only) */}
      <aside className="relative hidden overflow-hidden bg-primary-800 lg:flex lg:flex-col lg:justify-center lg:px-12">
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            background:
              "radial-gradient(600px 400px at 80% 10%, rgba(18,184,232,0.35), transparent 60%), radial-gradient(500px 400px at 10% 90%, rgba(11,99,206,0.5), transparent 60%)",
          }}
          aria-hidden="true"
        />
        <div className="relative max-w-md">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/20 px-3 py-1 text-xs font-semibold text-primary-100">
            <IconLanguage className="h-3.5 w-3.5" aria-hidden="true" />
            Wolof + Français
          </span>
          <h2 className="mt-5 text-3xl font-bold leading-tight text-white">
            Le copilote clinique pensé pour le Sénégal.
          </h2>
          <p className="mt-4 text-primary-100">
            Parler → Transcrire → Structurer → Vérifier → Valider. Une note reste un brouillon tant
            qu'un professionnel ne l'a pas validée.
          </p>
          <ul className="mt-8 space-y-3">
            {[
              { Icon: IconScribe, text: "Scribe clinique avec préservation du transcript original" },
              { Icon: IconCheckCircle, text: "Zéro donnée inventée : absent = « Non documenté »" },
              { Icon: IconSecurity, text: "RBAC par ressource, audit et accès exceptionnel encadré" },
            ].map(({ Icon, text }) => (
              <li key={text} className="flex items-start gap-3 text-sm text-primary-100">
                <Icon className="mt-0.5 h-5 w-5 shrink-0 text-accent" aria-hidden="true" />
                {text}
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  );
}
