import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../lib/auth";
import { useMeta } from "../lib/useMeta";
import { Logo } from "./Logo";
import { DemoBanner } from "./ui";

interface NavItem {
  to: string;
  label: string;
}

const PROFESSIONAL_NAV: NavItem[] = [
  { to: "/app", label: "Accueil" },
  { to: "/app/patients", label: "Patients" },
  { to: "/app/consultations", label: "Consultations" },
  { to: "/app/scribe", label: "Scribe" },
  { to: "/app/teleconsultation", label: "Téléconsultation" },
  { to: "/app/messages", label: "Messages" },
  { to: "/app/documents", label: "Documents" },
  { to: "/app/coordination", label: "Coordination" },
  { to: "/app/profile", label: "Profil" },
  { to: "/app/settings", label: "Paramètres" },
];

const PATIENT_NAV: NavItem[] = [
  { to: "/app", label: "Accueil" },
  { to: "/app/appointments", label: "Rendez-vous" },
  { to: "/app/consultations", label: "Consultations" },
  { to: "/app/documents", label: "Documents" },
  { to: "/app/teleconsultation", label: "Téléconsultations" },
  { to: "/app/messages", label: "Messages" },
  { to: "/app/consents", label: "Consentements" },
  { to: "/app/profile", label: "Profil" },
];

const ORG_NAV: NavItem[] = [
  { to: "/app", label: "Tableau de bord" },
  { to: "/app/professionals", label: "Professionnels" },
  { to: "/app/patients", label: "Patients autorisés" },
  { to: "/app/consultations", label: "Consultations" },
  { to: "/app/services", label: "Services" },
  { to: "/app/appointments", label: "Rendez-vous" },
  { to: "/app/documents", label: "Documents" },
  { to: "/app/coordination", label: "Coordination" },
  { to: "/app/billing", label: "Abonnement" },
  { to: "/app/settings", label: "Paramètres" },
];

const ADMIN_NAV: NavItem[] = [
  { to: "/app", label: "Accueil" },
  { to: "/app/admin/users", label: "Utilisateurs" },
  { to: "/app/admin/organizations", label: "Structures" },
  { to: "/app/admin/verifications", label: "Vérifications" },
  { to: "/app/admin/subscriptions", label: "Abonnements" },
  { to: "/app/admin/payments", label: "Paiements" },
  { to: "/app/admin/security", label: "Sécurité" },
  { to: "/app/admin/audit", label: "Audit" },
  { to: "/app/admin/support", label: "Support" },
  { to: "/app/admin/config", label: "Configuration" },
];

function navFor(role: string | undefined): NavItem[] {
  if (role === "platform_admin") return ADMIN_NAV;
  if (role === "patient") return PATIENT_NAV;
  if (role === "org_admin") return ORG_NAV;
  return PROFESSIONAL_NAV;
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const { meta } = useMeta();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const items = navFor(user?.role);

  return (
    <div className="min-h-screen bg-slate-50">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2"
      >
        Aller au contenu principal
      </a>

      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              className="btn-ghost lg:hidden"
              aria-expanded={open}
              aria-controls="app-nav"
              onClick={() => setOpen((v) => !v)}
            >
              <span aria-hidden="true">☰</span>
              <span className="sr-only">Ouvrir le menu</span>
            </button>
            <Logo />
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden text-sm text-muted sm:inline">{user?.full_name}</span>
            <button
              className="btn-secondary"
              onClick={() => {
                logout();
                navigate("/");
              }}
            >
              Déconnexion
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6">
        <nav
          id="app-nav"
          aria-label="Navigation principale"
          className={`${open ? "block" : "hidden"} w-full shrink-0 lg:block lg:w-56`}
        >
          <ul className="space-y-1">
            {items.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === "/app"}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `block rounded-xl px-3 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-primary text-white"
                        : "text-ink hover:bg-primary-light hover:text-primary-dark"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <main id="main" className="min-w-0 flex-1">
          {meta?.demo_banner && <DemoBanner capabilities={meta.capabilities} />}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
