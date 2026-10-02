import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { useAuth } from "./lib/auth";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";
import { Patients } from "./pages/Patients";
import { PatientDetail } from "./pages/PatientDetail";
import { Scribe } from "./pages/Scribe";
import { Status } from "./pages/Status";
import { Billing } from "./pages/Billing";
import { ListSkeleton } from "./components/ui";
import {
  Appointments,
  Consents,
  Coordination,
  Documents,
  Messages,
  Notifications,
  Profile,
  Settings,
  Teleconsultation,
} from "./pages/Misc";
import {
  AdminAudit,
  AdminConfig,
  AdminOrganizations,
  AdminPayments,
  AdminSecurity,
  AdminSubscriptions,
  AdminSupport,
  AdminUsers,
  AdminVerifications,
} from "./pages/Admin";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <ListSkeleton rows={3} />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

/** Placeholder for sections that are explicitly "en préparation". */
function ComingSoon({ title }: { title: string }) {
  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight text-ink">{title}</h1>
      <div className="card mt-4">
        <p className="font-semibold text-ink">Fonctionnalité en préparation</p>
        <p className="mt-1 text-sm text-muted">
          Cette section est prévue dans l'architecture et n'est pas encore active. Aucune donnée
          fictive n'est affichée en attendant.
        </p>
      </div>
    </div>
  );
}

function ConsentsRoute() {
  const { patientId } = useParams();
  return <Consents patientId={patientId} />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/status" element={<Status />} />

      <Route
        path="/app"
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="patients" element={<Patients />} />
        <Route path="patients/:patientId" element={<PatientDetail />} />
        <Route path="patients/:patientId/consents" element={<ConsentsRoute />} />
        <Route path="consultations" element={<ComingSoon title="Consultations" />} />
        <Route path="scribe" element={<Scribe />} />
        <Route path="teleconsultation" element={<Teleconsultation />} />
        <Route path="messages" element={<Messages />} />
        <Route path="documents" element={<Documents />} />
        <Route path="coordination" element={<Coordination />} />
        <Route path="appointments" element={<Appointments />} />
        <Route path="consents" element={<Consents />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="profile" element={<Profile />} />
        <Route path="settings" element={<Settings />} />
        <Route path="billing" element={<Billing />} />
        <Route path="services" element={<ComingSoon title="Services" />} />
        <Route path="professionals" element={<ComingSoon title="Professionnels" />} />

        <Route path="admin/users" element={<AdminUsers />} />
        <Route path="admin/organizations" element={<AdminOrganizations />} />
        <Route path="admin/verifications" element={<AdminVerifications />} />
        <Route path="admin/subscriptions" element={<AdminSubscriptions />} />
        <Route path="admin/payments" element={<AdminPayments />} />
        <Route path="admin/security" element={<AdminSecurity />} />
        <Route path="admin/audit" element={<AdminAudit />} />
        <Route path="admin/support" element={<AdminSupport />} />
        <Route path="admin/config" element={<AdminConfig />} />
      </Route>

      <Route
        path="*"
        element={
          <div className="mx-auto max-w-lg px-4 py-20 text-center">
            <h1 className="text-2xl font-bold text-ink">Page introuvable</h1>
            <p className="mt-2 text-sm text-muted">
              Cette page n'existe pas. Vérifiez l'adresse ou revenez à l'accueil.
            </p>
            <a href="/" className="btn-primary mt-6">
              Retour à l'accueil
            </a>
          </div>
        }
      />
    </Routes>
  );
}
