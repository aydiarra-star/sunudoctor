import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Patient } from "../lib/api";
import {
  Avatar,
  CardSkeleton,
  ErrorState,
  PageHeader,
  StatusPill,
} from "../components/ui";
import {
  IconArrowLeft,
  IconVitals,
  IconMedication,
  IconWarning,
  IconDocuments,
  IconSecurity,
  IconRecords,
  IconConsultation,
} from "../components/icons";

interface Allergy {
  id: string;
  substance: string;
  reaction: string | null;
  uncertain: boolean;
}
interface Medication {
  id: string;
  name: string;
  dose: string | null;
  uncertain: boolean;
}
interface Observation {
  id: string;
  label: string;
  value: string;
  unit: string | null;
  uncertain: boolean;
  recorded_at: string;
}
interface PatientDetailResponse {
  patient: Patient;
  allergies: Allergy[];
  medications: Medication[];
  observations: Observation[];
}

const TABS = [
  { key: "resume", label: "Résumé", Icon: IconRecords },
  { key: "consultations", label: "Consultations", Icon: IconConsultation },
  { key: "antecedents", label: "Antécédents", Icon: IconVitals },
  { key: "medicaments", label: "Médicaments", Icon: IconMedication },
  { key: "allergies", label: "Allergies", Icon: IconWarning },
  { key: "documents", label: "Documents", Icon: IconDocuments },
  { key: "consentements", label: "Consentements", Icon: IconSecurity },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function Undocumented({ label }: { label: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-200 px-4 py-6 text-center">
      <p className="text-sm font-medium text-ink">{label}</p>
      <p className="mt-1 text-xs text-muted">Non documenté</p>
    </div>
  );
}

export function PatientDetail() {
  const { patientId } = useParams();
  const [data, setData] = useState<PatientDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabKey>("resume");

  useEffect(() => {
    if (!patientId) return;
    setError(null);
    api
      .get<PatientDetailResponse>(`/patients/${patientId}`)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, [patientId]);

  if (error) {
    return (
      <div>
        <BackLink />
        <ErrorState message={error} />
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <BackLink />
        <CardSkeleton />
      </div>
    );
  }

  const { patient, allergies, medications, observations } = data;

  return (
    <div>
      <BackLink />

      <PageHeader
        title={`${patient.first_name} ${patient.last_name}`}
        subtitle={[patient.region, patient.phone].filter(Boolean).join(" · ") || "Coordonnées non documentées"}
      />

      <div className="mb-5 flex flex-wrap items-center gap-4 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-soft">
        <Avatar name={`${patient.first_name} ${patient.last_name}`} size={52} />
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-2 font-semibold text-ink">
            {patient.first_name} {patient.last_name}
            {patient.is_demo && <span className="badge-demo">DEMO</span>}
          </p>
          <p className="text-sm text-muted">
            Né(e) le{" "}
            {patient.date_of_birth
              ? new Date(patient.date_of_birth).toLocaleDateString("fr-FR")
              : "Non documenté"}{" "}
            · {patient.sex ?? "Sexe non documenté"}
          </p>
        </div>
        <StatusPill status="verified" />
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-1.5 overflow-x-auto pb-1" role="tablist" aria-label="Sections du dossier">
        {TABS.map(({ key, label, Icon }) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`flex shrink-0 items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-medium transition-colors ${
              tab === key
                ? "bg-primary text-white"
                : "border border-slate-200 bg-white text-muted hover:text-ink"
            }`}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>

      {tab === "resume" && (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="card lg:col-span-2">
            <h2 className="font-semibold text-ink">Constantes</h2>
            {observations.length === 0 ? (
              <div className="mt-3">
                <Undocumented label="Aucune constante enregistrée" />
              </div>
            ) : (
              <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                {observations.map((o) => (
                  <li
                    key={o.id}
                    className="flex items-center justify-between rounded-xl bg-surface px-3 py-2"
                  >
                    <span className="text-sm text-muted">{o.label}</span>
                    <span className="text-sm font-semibold text-ink">
                      {o.value} {o.unit ?? ""}
                      {o.uncertain && <span className="badge-warn ml-2">À vérifier</span>}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="card">
            <h2 className="font-semibold text-ink">Alertes</h2>
            <div className="mt-3 space-y-2">
              <p className="flex items-center gap-2 text-sm text-muted">
                <IconWarning className="h-4 w-4 text-orange-500" aria-hidden="true" />
                Allergies : {allergies.length === 0 ? "Non documenté" : allergies.length}
              </p>
              <p className="flex items-center gap-2 text-sm text-muted">
                <IconMedication className="h-4 w-4 text-primary" aria-hidden="true" />
                Traitements : {medications.length === 0 ? "Non documenté" : medications.length}
              </p>
            </div>
          </div>
        </div>
      )}

      {tab === "antecedents" && (
        <div className="card">
          <h2 className="font-semibold text-ink">Antécédents</h2>
          <div className="mt-3">
            <Undocumented label="Aucun antécédent documenté" />
          </div>
        </div>
      )}

      {tab === "consultations" && (
        <div className="card">
          <h2 className="font-semibold text-ink">Consultations</h2>
          <div className="mt-3">
            <Undocumented label="Aucune consultation documentée" />
          </div>
          <Link to="/app/scribe" className="btn-primary mt-4">
            Démarrer le Scribe
          </Link>
        </div>
      )}

      {tab === "medicaments" && (
        <div className="card">
          <h2 className="font-semibold text-ink">Médicaments</h2>
          {medications.length === 0 ? (
            <div className="mt-3">
              <Undocumented label="Aucun traitement documenté" />
            </div>
          ) : (
            <ul className="mt-3 space-y-2">
              {medications.map((m) => (
                <li key={m.id} className="flex items-center justify-between rounded-xl bg-surface px-3 py-2">
                  <span className="text-sm font-medium text-ink">{m.name}</span>
                  <span className="text-sm text-muted">
                    {m.dose ?? "Dose non documentée"}
                    {m.uncertain && <span className="badge-warn ml-2">À vérifier</span>}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {tab === "allergies" && (
        <div className="card">
          <h2 className="font-semibold text-ink">Allergies</h2>
          {allergies.length === 0 ? (
            <div className="mt-3">
              <Undocumented label="Aucune allergie documentée" />
            </div>
          ) : (
            <ul className="mt-3 space-y-2">
              {allergies.map((a) => (
                <li key={a.id} className="flex items-center justify-between rounded-xl bg-surface px-3 py-2">
                  <span className="text-sm font-medium text-ink">{a.substance}</span>
                  <span className="text-sm text-muted">
                    {a.reaction ?? "Réaction non documentée"}
                    {a.uncertain && <span className="badge-warn ml-2">À vérifier</span>}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {tab === "documents" && (
        <div className="card">
          <h2 className="font-semibold text-ink">Documents</h2>
          <div className="mt-3">
            <Undocumented label="Aucun document" />
          </div>
          <Link to="/app/documents" className="btn-secondary mt-4">
            Voir tous les documents
          </Link>
        </div>
      )}

      {tab === "consentements" && (
        <div className="card">
          <h2 className="font-semibold text-ink">Consentements</h2>
          <p className="mt-2 text-sm text-muted">
            Accès, partage, téléconsultation, conservation audio, assistance IA et recherche.
          </p>
          <Link to={`/app/patients/${patient.id}/consents`} className="btn-secondary mt-4">
            Gérer les consentements
          </Link>
        </div>
      )}
    </div>
  );
}

function BackLink() {
  return (
    <Link
      to="/app/patients"
      className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-primary"
    >
      <IconArrowLeft className="h-4 w-4" aria-hidden="true" />
      Tous les patients
    </Link>
  );
}
