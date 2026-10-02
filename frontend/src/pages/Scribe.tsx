import { useEffect, useState } from "react";
import { api, type Consultation, type Patient, type StructuredNote } from "../lib/api";
import { EmptyState, ErrorState, PageHeader, Spinner } from "../components/ui";

type Step = "idle" | "recording" | "transcribed" | "structured" | "validated";

interface TranscribeResponse {
  transcription_id: string;
  raw_text: string;
  language: string;
  provider: string;
  is_demo: boolean;
  demo_banner: string | null;
  uncertain_spans: string[];
  audio_retained: boolean;
}

interface StructureResponse {
  structured_note_id: string;
  status: string;
  disclaimer: string;
  is_demo: boolean;
  demo_banner: string | null;
  structured: StructuredNote;
  safety_flags: string[];
  uncertainties: string[];
}

const EXAMPLE = "Patient bi dafa am douleur ci ventre bi depuis trois days, te fièvre du.";

export function Scribe() {
  const [patients, setPatients] = useState<Patient[] | null>(null);
  const [patientId, setPatientId] = useState("");
  const [step, setStep] = useState<Step>("idle");
  const [consultation, setConsultation] = useState<Consultation | null>(null);
  const [transcript, setTranscript] = useState<TranscribeResponse | null>(null);
  const [note, setNote] = useState<StructureResponse | null>(null);
  const [textHint, setTextHint] = useState("");
  const [consentAudio, setConsentAudio] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [decision, setDecision] = useState("");

  useEffect(() => {
    api
      .get<Patient[]>("/patients")
      .then(setPatients)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, []);

  async function startConsultation() {
    setError(null);
    setBusy(true);
    try {
      const cons = await api.post<Consultation>("/scribe/consultations", {
        patient_id: patientId,
      });
      setConsultation(cons);
      setStep("recording");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Impossible de démarrer");
    } finally {
      setBusy(false);
    }
  }

  async function transcribe() {
    if (!consultation) return;
    setError(null);
    setBusy(true);
    try {
      const res = await api.post<TranscribeResponse>("/scribe/transcribe", {
        consultation_id: consultation.id,
        language_hint: "wolof",
        text_hint: textHint,
        consent_audio: consentAudio,
      });
      setTranscript(res);
      setStep("transcribed");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Transcription impossible");
    } finally {
      setBusy(false);
    }
  }

  async function structure() {
    if (!transcript) return;
    setError(null);
    setBusy(true);
    try {
      const res = await api.post<StructureResponse>("/scribe/structure", {
        transcription_id: transcript.transcription_id,
      });
      setNote(res);
      setStep("structured");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Structuration impossible");
    } finally {
      setBusy(false);
    }
  }

  async function validate() {
    if (!consultation) return;
    setError(null);
    setBusy(true);
    try {
      await api.post(`/scribe/consultations/${consultation.id}/validate`, {
        decision,
        change_note: "Validation par le professionnel",
      });
      setStep("validated");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Validation impossible");
    } finally {
      setBusy(false);
    }
  }

  const steps: Array<{ key: Step; label: string }> = [
    { key: "recording", label: "Enregistrement" },
    { key: "transcribed", label: "Transcription" },
    { key: "structured", label: "Structuration" },
    { key: "validated", label: "Validation" },
  ];
  const stepIndex = steps.findIndex((s) => s.key === step);

  return (
    <div>
      <PageHeader
        title="Scribe clinique"
        subtitle="Parler → Transcrire → Structurer → Vérifier → Valider"
      />

      {error && <ErrorState message={error} />}

      <ol className="mb-5 flex flex-wrap gap-2" aria-label="Étapes">
        {steps.map((s, i) => (
          <li
            key={s.key}
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              i <= stepIndex && step !== "idle"
                ? "bg-primary text-white"
                : "bg-slate-200 text-slate-600"
            }`}
            aria-current={s.key === step ? "step" : undefined}
          >
            {i + 1}. {s.label}
          </li>
        ))}
      </ol>

      {/* Step 1: choose patient + start */}
      {step === "idle" && (
        <div className="card">
          {patients === null && <Spinner />}
          {patients?.length === 0 && (
            <EmptyState
              title="Aucun patient autorisé"
              hint="Créez d'abord un dossier patient dans la section Patients."
            />
          )}
          {patients && patients.length > 0 && (
            <>
              <label className="label" htmlFor="patient">
                Patient
              </label>
              <select
                id="patient"
                className="input"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
              >
                <option value="">— Sélectionner —</option>
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name} {p.is_demo ? "(DEMO)" : ""}
                  </option>
                ))}
              </select>
              <button
                className="btn-primary mt-4"
                disabled={!patientId || busy}
                onClick={startConsultation}
              >
                Démarrer le Scribe
              </button>
            </>
          )}
        </div>
      )}

      {/* Step 2: recording / transcription input */}
      {step === "recording" && (
        <div className="card">
          <div className="flex flex-col items-center gap-3 py-4">
            <span
              className="flex h-20 w-20 items-center justify-center rounded-full bg-primary text-3xl text-white"
              aria-hidden="true"
            >
              🎙
            </span>
            <p className="font-semibold text-ink">Enregistrement</p>
            <p className="max-w-md text-center text-sm text-muted">
              Aucun moteur de reconnaissance vocale réel n'est configuré (mode démonstration). Saisissez
              la transcription ci-dessous pour exercer la chaîne complète.
            </p>
          </div>

          <label className="label" htmlFor="hint">
            Transcription (mode démonstration)
          </label>
          <textarea
            id="hint"
            className="input min-h-24"
            placeholder={EXAMPLE}
            value={textHint}
            onChange={(e) => setTextHint(e.target.value)}
          />
          <button
            type="button"
            className="btn-ghost mt-2 text-xs"
            onClick={() => setTextHint(EXAMPLE)}
          >
            Utiliser l'exemple Wolof/Français
          </button>

          <label className="mt-4 flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={consentAudio}
              onChange={(e) => setConsentAudio(e.target.checked)}
            />
            Consentement pour la conservation de l'audio original
          </label>

          <button
            className="btn-primary mt-4"
            disabled={busy || textHint.trim().length === 0}
            onClick={transcribe}
          >
            {busy ? "Transcription…" : "Transcrire"}
          </button>
        </div>
      )}

      {/* Transcript */}
      {transcript && step !== "recording" && (
        <div className="card mt-4">
          <h2 className="font-semibold text-ink">Transcription brute</h2>
          {transcript.is_demo && (
            <p className="mt-1 text-xs text-amber-700">
              Mode démonstration — transcription saisie, non issue d'un moteur vocal.
            </p>
          )}
          <p className="mt-2 whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-ink">
            {transcript.raw_text || "Non documenté"}
          </p>
          <p className="mt-2 text-xs text-muted">
            Audio conservé : {transcript.audio_retained ? "oui (consentement donné)" : "non"}
          </p>
          {step === "transcribed" && (
            <button className="btn-primary mt-4" disabled={busy} onClick={structure}>
              {busy ? "Structuration…" : "Structurer la note"}
            </button>
          )}
        </div>
      )}

      {/* Structured note */}
      {note && (
        <div className="card mt-4 border-amber-300">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-semibold text-ink">Note structurée</h2>
            <span className="badge-warn">BROUILLON IA</span>
          </div>
          <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {note.disclaimer}
          </p>

          <NoteView note={note.structured} />

          {note.safety_flags.length > 0 && (
            <div className="mt-4 rounded-lg border border-orange-200 bg-orange-50 p-3">
              <p className="text-sm font-semibold text-orange-900">⚠ Passage incertain — à vérifier</p>
              <ul className="mt-1 list-disc pl-5 text-xs text-orange-800">
                {note.safety_flags.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}

          {step === "structured" && (
            <div className="mt-5 border-t border-slate-200 pt-4">
              <label className="label" htmlFor="decision">
                Décision du professionnel (saisie humaine)
              </label>
              <textarea
                id="decision"
                className="input min-h-20"
                value={decision}
                onChange={(e) => setDecision(e.target.value)}
                placeholder="Votre décision clinique…"
              />
              <div className="mt-3 flex flex-wrap gap-2">
                <button className="btn-primary" disabled={busy} onClick={validate}>
                  {busy ? "Validation…" : "Confirmer et valider"}
                </button>
                <button className="btn-secondary" onClick={() => setNote(null)}>
                  Modifier
                </button>
                <button className="btn-danger" onClick={() => setStep("recording")}>
                  Rejeter
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {step === "validated" && (
        <div className="card mt-4 border-emerald-300 bg-emerald-50" role="status">
          <p className="font-semibold text-emerald-800">Consultation validée</p>
          <p className="mt-1 text-sm text-emerald-700">
            La note est validée et historisée. Seul un professionnel peut valider une note.
          </p>
        </div>
      )}
    </div>
  );
}

function Field({ label, value, uncertain }: { label: string; value: string | null; uncertain: boolean }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink">
        {value ?? <span className="text-muted">Non documenté</span>}
        {uncertain && <span className="badge-warn ml-2">À vérifier</span>}
      </dd>
    </div>
  );
}

function NoteView({ note }: { note: StructuredNote }) {
  return (
    <dl className="mt-4 grid gap-3 sm:grid-cols-2">
      <Field label="Motif" value={note.chief_complaint.value} uncertain={note.chief_complaint.uncertain} />
      <Field label="Histoire de la maladie" value={note.history.value} uncertain={note.history.uncertain} />
      <div>
        <dt className="text-xs font-semibold uppercase tracking-wide text-muted">Symptômes</dt>
        <dd className="mt-0.5 text-sm text-ink">
          {note.symptoms.length === 0 ? (
            <span className="text-muted">Non documenté</span>
          ) : (
            <ul className="list-disc pl-5">
              {note.symptoms.map((s, i) => (
                <li key={i}>
                  {s.value} {s.uncertain && <span className="badge-warn">À vérifier</span>}
                </li>
              ))}
            </ul>
          )}
        </dd>
      </div>
      <div>
        <dt className="text-xs font-semibold uppercase tracking-wide text-muted">Symptômes niés</dt>
        <dd className="mt-0.5 text-sm text-ink">
          {note.negated_symptoms.length === 0 ? (
            <span className="text-muted">Aucun</span>
          ) : (
            <ul className="list-disc pl-5">
              {note.negated_symptoms.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          )}
        </dd>
      </div>
      <div>
        <dt className="text-xs font-semibold uppercase tracking-wide text-muted">Traitements</dt>
        <dd className="mt-0.5 text-sm text-ink">
          {note.medications.length === 0 ? (
            <span className="text-muted">Non documenté</span>
          ) : (
            <ul className="list-disc pl-5">
              {note.medications.map((m, i) => (
                <li key={i}>
                  {m.name} {m.dose ?? ""} {m.uncertain && <span className="badge-warn">À vérifier</span>}
                </li>
              ))}
            </ul>
          )}
        </dd>
      </div>
      <div>
        <dt className="text-xs font-semibold uppercase tracking-wide text-muted">Constantes</dt>
        <dd className="mt-0.5 text-sm text-ink">
          {note.vitals.length === 0 ? (
            <span className="text-muted">Non documenté</span>
          ) : (
            <ul className="list-disc pl-5">
              {note.vitals.map((v, i) => (
                <li key={i}>
                  {v.label} : {v.value} {v.unit ?? ""}
                </li>
              ))}
            </ul>
          )}
        </dd>
      </div>
      <Field label="Diagnostic / hypothèse" value={note.diagnosis.value} uncertain={note.diagnosis.uncertain} />
      <Field label="Décision" value={note.decision.value} uncertain={note.decision.uncertain} />
      <Field label="Prescription" value={note.prescription.value} uncertain={note.prescription.uncertain} />
      <Field label="Recommandations" value={note.recommendations.value} uncertain={note.recommendations.uncertain} />
      <Field label="Suivi" value={note.follow_up.value} uncertain={note.follow_up.uncertain} />
    </dl>
  );
}
