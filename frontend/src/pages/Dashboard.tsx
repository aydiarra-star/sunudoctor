import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { PageHeader } from "../components/ui";

const CARDS: Record<string, Array<{ to: string; title: string; body: string }>> = {
  default: [
    { to: "/app/scribe", title: "Nouvelle consultation", body: "Démarrer le Scribe clinique." },
    { to: "/app/patients", title: "Patients", body: "Consulter les dossiers autorisés." },
    { to: "/app/teleconsultation", title: "Téléconsultation", body: "Vidéo — configuration requise." },
  ],
  patient: [
    { to: "/app/appointments", title: "Rendez-vous", body: "Demander ou consulter un rendez-vous." },
    { to: "/app/documents", title: "Mes documents", body: "Comptes rendus, prescriptions." },
    { to: "/app/consents", title: "Mes consentements", body: "Gérer accès, partage, IA." },
  ],
};

export function Dashboard() {
  const { user } = useAuth();
  const role = user?.role ?? "default";
  const cards = CARDS[role] ?? CARDS.default;

  const verification = user?.professional?.verification_status;

  return (
    <div>
      <PageHeader
        title={`Bonjour ${user?.full_name ?? ""}`}
        subtitle="Espace de travail SunuDoctor"
      />

      {verification && verification !== "verified" && (
        <div className="mb-4 rounded-xl border border-orange-300 bg-orange-50 px-4 py-3 text-sm text-orange-900">
          <p className="font-semibold">Vérification professionnelle : en cours</p>
          <p className="mt-0.5">
            Votre profil est en attente de vérification. Le statut « Vérifié » n'est jamais attribué
            automatiquement. Statut actuel : <strong>{verification}</strong>.
          </p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((c) => (
          <Link key={c.to} to={c.to} className="card transition-shadow hover:shadow-md">
            <h2 className="font-semibold text-ink">{c.title}</h2>
            <p className="mt-1 text-sm text-muted">{c.body}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
