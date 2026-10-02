import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "../lib/auth";
import { useMeta } from "../lib/useMeta";
import { useConnection } from "../lib/useConnection";
import { Logo } from "./Logo";
import { ConnectionPill, DemoBanner, Avatar } from "./ui";
import {
  IconHome,
  IconPatients,
  IconConsultation,
  IconScribe,
  IconTeleconsultation,
  IconMessages,
  IconDocuments,
  IconCoordination,
  IconProfile,
  IconSettings,
  IconLogout,
  IconMenu,
  IconClose,
  IconCalendar,
  IconSecurity,
  IconStructure,
  IconPayments,
  IconNotifications,
  IconRecords,
  IconBuilding2,
} from "./icons";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  to: string;
  label: string;
  Icon: LucideIcon;
  /** Show in the mobile bottom bar (kept to 5 max for touch comfort). */
  mobile?: boolean;
}

const PROFESSIONAL_NAV: NavItem[] = [
  { to: "/app", label: "Accueil", Icon: IconHome, mobile: true },
  { to: "/app/patients", label: "Patients", Icon: IconPatients, mobile: true },
  { to: "/app/scribe", label: "Scribe", Icon: IconScribe, mobile: true },
  { to: "/app/consultations", label: "Consultations", Icon: IconConsultation },
  { to: "/app/teleconsultation", label: "Téléconsultation", Icon: IconTeleconsultation, mobile: true },
  { to: "/app/messages", label: "Messages", Icon: IconMessages, mobile: true },
  { to: "/app/documents", label: "Documents", Icon: IconDocuments },
  { to: "/app/coordination", label: "Coordination", Icon: IconCoordination },
  { to: "/app/profile", label: "Profil", Icon: IconProfile },
  { to: "/app/settings", label: "Paramètres", Icon: IconSettings },
];

const PATIENT_NAV: NavItem[] = [
  { to: "/app", label: "Accueil", Icon: IconHome, mobile: true },
  { to: "/app/appointments", label: "Rendez-vous", Icon: IconCalendar, mobile: true },
  { to: "/app/teleconsultation", label: "Téléconsultations", Icon: IconTeleconsultation, mobile: true },
  { to: "/app/documents", label: "Documents", Icon: IconDocuments, mobile: true },
  { to: "/app/messages", label: "Messages", Icon: IconMessages, mobile: true },
  { to: "/app/consultations", label: "Consultations", Icon: IconConsultation },
  { to: "/app/consents", label: "Consentements", Icon: IconSecurity },
  { to: "/app/profile", label: "Profil", Icon: IconProfile },
];

const ORG_NAV: NavItem[] = [
  { to: "/app", label: "Tableau de bord", Icon: IconHome, mobile: true },
  { to: "/app/professionals", label: "Professionnels", Icon: IconStructure, mobile: true },
  { to: "/app/patients", label: "Patients autorisés", Icon: IconPatients, mobile: true },
  { to: "/app/appointments", label: "Rendez-vous", Icon: IconCalendar, mobile: true },
  { to: "/app/billing", label: "Abonnement", Icon: IconPayments, mobile: true },
  { to: "/app/consultations", label: "Consultations", Icon: IconConsultation },
  { to: "/app/services", label: "Services", Icon: IconBuilding2 },
  { to: "/app/documents", label: "Documents", Icon: IconDocuments },
  { to: "/app/coordination", label: "Coordination", Icon: IconCoordination },
  { to: "/app/settings", label: "Paramètres", Icon: IconSettings },
];

const ADMIN_NAV: NavItem[] = [
  { to: "/app", label: "Accueil", Icon: IconHome, mobile: true },
  { to: "/app/admin/users", label: "Utilisateurs", Icon: IconProfile, mobile: true },
  { to: "/app/admin/organizations", label: "Structures", Icon: IconStructure, mobile: true },
  { to: "/app/admin/verifications", label: "Vérifications", Icon: IconRecords, mobile: true },
  { to: "/app/admin/security", label: "Sécurité", Icon: IconSecurity, mobile: true },
  { to: "/app/admin/subscriptions", label: "Abonnements", Icon: IconPayments },
  { to: "/app/admin/payments", label: "Paiements", Icon: IconPayments },
  { to: "/app/admin/audit", label: "Audit", Icon: IconRecords },
  { to: "/app/admin/support", label: "Support", Icon: IconNotifications },
  { to: "/app/admin/config", label: "Configuration", Icon: IconSettings },
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
  const connection = useConnection();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const items = navFor(user?.role);
  const mobileItems = items.filter((i) => i.mobile).slice(0, 5);

  useEffect(() => {
    setOpen(false);
  }, [user?.role]);

  return (
    <div className="min-h-screen bg-surface">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2"
      >
        Aller au contenu principal
      </a>

      <div className="mx-auto flex max-w-[1500px]">
        {/* ----------------------------- Desktop sidebar ----------------------------- */}
        <aside
          className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-slate-200/80 bg-sidebar lg:flex"
          aria-label="Navigation principale"
        >
          <div className="flex h-16 items-center px-5">
            <NavLink to="/app">
              <Logo />
            </NavLink>
          </div>

          <nav className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
            <ul className="space-y-0.5">
              {items.map(({ to, label, Icon }) => (
                <li key={to}>
                  <NavLink
                    to={to}
                    end={to === "/app"}
                    className={({ isActive }) =>
                      `nav-item ${isActive ? "nav-item-active" : ""}`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
                        <span className="flex-1">{label}</span>
                        {isActive && (
                          <span
                            className="h-1.5 w-1.5 rounded-full bg-primary"
                            aria-hidden="true"
                          />
                        )}
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          {/* Sidebar footer: connection status, profile, settings */}
          <div className="border-t border-slate-200/80 p-3">
            <div className="mb-2 flex items-center justify-between rounded-xl bg-white px-3 py-2 shadow-soft">
              <ConnectionPill status={connection} />
              <NavLink
                to="/app/notifications"
                className="text-muted hover:text-ink"
                aria-label="Notifications"
              >
                <IconNotifications className="h-4 w-4" aria-hidden="true" />
              </NavLink>
            </div>
            <NavLink
              to="/app/profile"
              className="flex items-center gap-3 rounded-xl px-2 py-2 hover:bg-primary-50"
            >
              <Avatar name={user?.full_name ?? "?"} size={36} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold text-ink">
                  {user?.full_name}
                </span>
                <span className="block truncate text-xs text-muted">{user?.role}</span>
              </span>
            </NavLink>
            <button
              className="nav-item mt-1 w-full"
              onClick={() => {
                logout();
                navigate("/");
              }}
            >
              <IconLogout className="h-[18px] w-[18px]" aria-hidden="true" />
              Déconnexion
            </button>
          </div>
        </aside>

        {/* --------------------------------- Main ---------------------------------- */}
        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          {/* Mobile top bar */}
          <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur lg:hidden">
            <div className="flex items-center justify-between gap-3 px-4 py-3">
              <NavLink to="/app">
                <Logo size={32} />
              </NavLink>
              <div className="flex items-center gap-2">
                <ConnectionPill status={connection} label="" />
                <button
                  className="btn-ghost px-2"
                  aria-expanded={open}
                  aria-controls="mobile-drawer"
                  onClick={() => setOpen((v) => !v)}
                >
                  {open ? (
                    <IconClose className="h-5 w-5" aria-hidden="true" />
                  ) : (
                    <IconMenu className="h-5 w-5" aria-hidden="true" />
                  )}
                  <span className="sr-only">{open ? "Fermer le menu" : "Ouvrir le menu"}</span>
                </button>
              </div>
            </div>

            {open && (
              <div
                id="mobile-drawer"
                className="animate-fade-in-up border-t border-slate-200 bg-white px-3 py-3"
              >
                <ul className="grid grid-cols-2 gap-1.5">
                  {items.map(({ to, label, Icon }) => (
                    <li key={to}>
                      <NavLink
                        to={to}
                        end={to === "/app"}
                        className={({ isActive }) =>
                          `flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium ${
                            isActive ? "bg-primary-100 text-primary-800" : "text-slate-600"
                          }`
                        }
                      >
                        <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
                        {label}
                      </NavLink>
                    </li>
                  ))}
                </ul>
                <button
                  className="btn-secondary mt-3 w-full"
                  onClick={() => {
                    logout();
                    navigate("/");
                  }}
                >
                  <IconLogout className="h-4 w-4" aria-hidden="true" />
                  Déconnexion
                </button>
              </div>
            )}
          </header>

          <main id="main" className="min-w-0 flex-1 px-4 pb-24 pt-5 sm:px-6 lg:pb-8 lg:pt-8">
            <div className="mx-auto max-w-6xl">
              {meta?.demo_banner && <DemoBanner capabilities={meta.capabilities} />}
              <Outlet />
            </div>
          </main>
        </div>
      </div>

      {/* ------------------------------ Mobile bottom nav ------------------------------ */}
      <nav
        className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 backdrop-blur lg:hidden"
        aria-label="Navigation principale mobile"
      >
        <ul className="mx-auto flex max-w-lg items-stretch justify-around px-1 pb-[max(0.25rem,env(safe-area-inset-bottom))] pt-1">
          {mobileItems.map(({ to, label, Icon }) => (
            <li key={to} className="flex-1">
              <NavLink
                to={to}
                end={to === "/app"}
                className={({ isActive }) =>
                  `flex min-h-[56px] flex-col items-center justify-center gap-0.5 rounded-xl px-1 py-1 text-[11px] font-medium transition-colors ${
                    isActive ? "text-primary" : "text-slate-500"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className="h-5 w-5" aria-hidden="true" />
                    <span className={isActive ? "font-semibold" : undefined}>{label}</span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
