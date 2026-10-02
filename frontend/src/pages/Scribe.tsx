import { useEffect, useState } from "react";
import { api, type Consultation, type Patient, type StructuredNote } from "../lib/api";
import type { LanguageDetection, DraftValidation, Meta } from "../lib/api";
import { blobToBase64, useRecorder } from "../lib/recorder";
import {
  EmptyState,
  ErrorState,
  ListSkeleton,
  PageHeader,
  useToast,
} from "../components/ui";
import {
  IconScribe,
  IconMic,
  IconStop,
  IconCheck,
  IconWarning,
  IconLanguage,
  IconCheckCircle,
  IconAI,
  IconInfo,
} from "../components/icons";

type Step = "idle" | "recording" | "transcribed" | "structured" | "validated";

interface TranscribeResponse {
  transcription_id: string;
  raw_text: string;
  language: string;
  provider: string;
  is_demo: boolean;
  demo_banner: string | null;
  uncertain_spans: string[];
  confidence: number | null;
  duration_seconds: number | null;
  segments: Array<{
    start: number;
    end: number;
    text: string;
    language: string | null;
    confidence: number | null;
  }>;
  audio_retained: boolean;
  detection: LanguageDetection | null;
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
  validation: DraftValidation;
}

const EXAMPLE = "Patient bi dafa am douleur ci ventre bi depuis trois days, te fièvre du.";

const PIPELINE: Array<{ key: Step; label: string }> = [
  { key: "recording", label: "Parler" },
  { key: "transcribed", label: "Transcrire" },
  { key: "structured", label: "Structurer" },
  { key: "structured", label: "Vérifier" },
  { key: "validated", label: "Valider" },
];

/** Visual progression: Parler → Transcrire → Structurer → Vérifier → Valider. */
function Pipeline({ step }: { step: Step }) {
  const order: Step[] = ["idle", "recording", "transcribed", "structured", "validated"];
  const current = order.indexOf(step);
  // The "Vérifier" step shares the structured stage; show it as reached once structured.
  const reached = (i: number) => {
    if (step === "idle") return false;
    if (i === 4) return step === "validated";
    if (i === 3) return step === "structured" || step === "validated";
    return current >= i;
  };
  return (
    <ol className="mb-6 flex items-center gap-1 overflow-x-auto" aria-label="Étapes du Scribe">
      {PIPELINE.map((p, i) => (
        <li key={p.label} className="flex flex-1 items-center gap-1">
          <div className="flex flex-1 flex-col items-center gap-1.5">
            <span
              className={`flex h-9 w-9 items-center justify-center rounded-full border-2 text-sm font-bold transition-colors ${
                reached(i)
                  ? "border-primary bg-primary text-white"
                  : "border-slate-200 bg-white text-slate-400"
              }`}
              aria-current={reached(i) && !reached(i + 1) ? "step" : undefined}
            >
              {reached(i) && step !== "recording" && i < current ? (
                <IconCheck className="h-4 w-4" aria-hidden="true" />
              ) : (
                i + 1
              )}
            </span>
            <span
              className={`text-xs font-medium ${reached(i) ? "text-primary-800" : "text-muted"}`}
            >
              {p.label}
            </span>
          </div>
          {i < PIPELINE.length - 1 && (
            <span
              className={`mb-5 h-0.5 flex-1 rounded ${reached(i + 1) ? "bg-primary" : "bg-slate-200"}`}
              aria-hidden="true"
            />
          )}
        </li>
      ))}
    </ol>
  );
}

function Waveform() {
  const bars = [0.45, 0.85, 0.4, 1, 0.6, 0.9, 0.35, 0.75, 0.5, 0.95, 0.45, 0.7, 0.55, 0.8];
  return (
    <div className="flex h-10 items-end justify-center gap-0.5" aria-hidden="true">
      {bars.map((h, i) => (
        <span
          key={i}
          className="w-1.5 animate-wave rounded-full bg-accent"
          style={{ height: `${h * 100}%`, animationDelay: `${i * 60}ms` }}
        />
      ))}
    </div>
  );
}

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
  const [meta, setMeta] = useState<Meta | null>(null);
  const [captured, setCaptured] = useState<Blob | null>(null);
  const recorder = useRecorder();
  const toast = useToast();

  useEffect(() => {
    api
      .get<Patient[]>("/patients")
      .then(setPatients)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
    api.get<Meta>("/meta").then(setMeta).catch(() => undefined);
  }, []);

  const sttLive = meta?.providers?.stt?.connected ?? false;

  async function startConsultation() {
    setError(null);
    setBusy(true);
    try {
      const cons = await api.post<Consultation>("/scribe/consultations", { patient_id: patientId });
      setConsultation(cons);
      setStep("recording");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Impossible de démarrer");
    } finally {
      setBusy(false);
    }
  }

  /** Send audio (real STT) or a typed hint (demo) to the backend. */
  async function transcribe(audio?: Blob | null) {
    if (!consultation) return;
    setError(null);
    setBusy(true);
    try {
      let audioBase64: string | undefined;
      if (audio && sttLive) {
        audioBase64 = await blobToBase64(audio);
      }
      const res = await api.post<TranscribeResponse>("/scribe/transcribe", {
        consultation_id: consultation.id,
        language_hint: "wolof",
        text_hint: audio && sttLive ? undefined : textHint,
        consent_audio: consentAudio,
        audio_base64: audioBase64,
      });
      setTranscript(res);
      setStep("transcribed");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Transcription impossible");
    } finally {
      setBusy(false);
    }
  }

  async function handleStopAndTranscribe() {
    const blob = await recorder.stop();
    setCaptured(blob);
    await transcribe(blob);
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
      toast.push({ title: "Consultation validée", body: "La note est historisée.", tone: "success" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Validation impossible");
    } finally {
      setBusy(false);
    }
  }

  const mmss = `${String(Math.floor(recorder.seconds / 60)).padStart(2, "0")}:${String(
    recorder.seconds % 60,
  ).padStart(2, "0")}`;

  return (
    <div>
      <PageHeader
        title="Scribe clinique"
        subtitle="Parler → Transcrire → Structurer → Vérifier → Valider"
        icon={<IconScribe className="h-5 w-5" aria-hidden="true" />}
      />

      <Pipeline step={step} />

      {error && <ErrorState message={error} />}

      {/* Step 1 — choose patient */}
      {step === "idle" && (
        <div className="card">
          {patients === null && <ListSkeleton rows={2} />}
          {patients?.length === 0 && (
            <EmptyState
              icon={<IconScribe className="h-6 w-6" aria-hidden="true" />}
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
                <IconMic className="h-4 w-4" aria-hidden="true" />
                Démarrer le Scribe
              </button>
            </>
          )}
        </div>
      )}

      {/* Step 2 — recording / transcription */}
      {step === "recording" && (
        <div className="card">
          <div className="flex flex-col items-center gap-4 py-4">
            <span
              className={`relative flex h-24 w-24 items-center justify-center rounded-full text-white ${
                recorder.state === "recording" ? "bg-primary" : "bg-slate-300"
              }`}
            >
              <IconMic className="h-10 w-10" aria-hidden="true" />
              {recorder.state === "recording" && (
                <span className="absolute inset-0 animate-pulse-ring rounded-full bg-primary/40" />
              )}
            </span>
            <div className="text-center">
              <p className="font-semibold text-ink">
                {recorder.state === "recording"
                  ? "Enregistrement en cours"
                  : recorder.state === "paused"
                    ? "Enregistrement en pause"
                    : recorder.state === "stopped"
                      ? "Enregistrement terminé"
                      : "Prêt à enregistrer"}
              </p>
              <p className="mt-0.5 font-mono text-2xl font-bold text-primary">{mmss}</p>
            </div>
            {recorder.state === "recording" && <Waveform />}

            <span className={sttLive ? "badge-ok" : "badge-warn"}>
              <IconWarning className="h-3 w-3" aria-hidden="true" />
              {sttLive
                ? "Reconnaissance vocale connectée"
                : "Reconnaissance vocale — configuration requise"}
            </span>
            {!sttLive && (
              <p className="max-w-md text-center text-sm text-muted">
                Aucun moteur de reconnaissance vocale réel n'est configuré. Vous pouvez enregistrer
                votre voix, mais la transcription automatique nécessite un moteur STT configuré
                côté serveur. Sinon, saisissez la transcription ci-dessous pour exercer la chaîne
                complète. L'audio n'est jamais simulé.
              </p>
            )}
            {recorder.error && (
              <p className="max-w-md text-center text-sm text-red-600" role="alert">
                {recorder.error}
              </p>
            )}

            <div className="flex flex-wrap items-center justify-center gap-2">
              {recorder.state === "idle" || recorder.state === "stopped" ? (
                <button className="btn-primary" onClick={() => recorder.start()} disabled={busy}>
                  <IconMic className="h-4 w-4" aria-hidden="true" />
                  Démarrer l'enregistrement
                </button>
              ) : (
                <>
                  {recorder.state === "recording" ? (
                    <button className="btn-secondary" onClick={recorder.pause}>
                      Pause
                    </button>
                  ) : (
                    <button className="btn-secondary" onClick={recorder.resume}>
                      Reprendre
                    </button>
                  )}
                  <button className="btn-primary" disabled={busy} onClick={handleStopAndTranscribe}>
                    <IconStop className="h-4 w-4" aria-hidden="true" />
                    Arrêter et transcrire
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="mt-2 border-t border-slate-100 pt-4">
            <div className="mb-2 flex items-center justify-between">
              <label className="label mb-0" htmlFor="hint">
                {sttLive
                  ? "Transcription manuelle de secours (facultative)"
                  : "Transcription (mode démonstration)"}
              </label>
              <span className="badge-info">
                <IconLanguage className="h-3 w-3" aria-hidden="true" />
                Wolof + Français
              </span>
            </div>
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
              onClick={() => transcribe(null)}
            >
              {busy ? (
                "Transcription…"
              ) : (
                <>
                  <IconStop className="h-4 w-4" aria-hidden="true" />
                  Transcrire le texte saisi
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Transcript — original preserved for comparison */}
      {transcript && step !== "recording" && (
        <div className="card mt-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-semibold text-ink">Transcript original</h2>
            <span className="badge-info">
              <IconLanguage className="h-3 w-3" aria-hidden="true" />
              Langue détectée :{" "}
              {transcript.detection?.mixed
                ? "Wolof + Français"
                : transcript.detection?.primary === "français"
                  ? "Français"
                  : "Wolof"}
            </span>
          </div>
          {transcript.is_demo && (
            <p className="mt-1.5 flex items-center gap-1.5 text-xs text-amber-700">
              <IconInfo className="h-3.5 w-3.5" aria-hidden="true" />
              Mode démonstration — transcription saisie, non issue d'un moteur vocal.
            </p>
          )}
          <p className="mt-2 whitespace-pre-wrap rounded-xl bg-surface p-3 text-sm text-ink">
            {transcript.raw_text || "Non documenté"}
          </p>
          {transcript.segments.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                Segments (horodatés)
              </p>
              <ul className="mt-1 space-y-1">
                {transcript.segments.map((seg, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-muted">
                    <span className="badge-muted shrink-0 font-mono">
                      {seg.start.toFixed(1)}–{seg.end.toFixed(1)}s
                    </span>
                    <span>{seg.text}</span>
                    {seg.confidence != null && (
                      <span className="shrink-0 text-[10px]">
                        ({Math.round(seg.confidence * 100)}%)
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="mt-2 text-xs text-muted">
            Audio conservé : {transcript.audio_retained ? "oui (consentement donné)" : "non"}
            {transcript.duration_seconds != null &&
              ` · Durée : ${transcript.duration_seconds.toFixed(1)} s`}
            {captured && ` · Audio capturé : ${(captured.size / 1024).toFixed(0)} Ko`}
          </p>
          {step === "transcribed" && (
            <button className="btn-primary mt-4" disabled={busy} onClick={structure}>
              {busy ? (
                "Structuration…"
              ) : (
                <>
                  <IconAI className="h-4 w-4" aria-hidden="true" />
                  Structurer la note
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Structured note — always a draft */}
      {note && (
        <div className="card mt-4 border-amber-300">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-semibold text-ink">Synthèse structurée</h2>
            <span className="badge-warn">BROUILLON IA</span>
          </div>
          <p className="mt-2 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {note.disclaimer}
          </p>

          <NoteView note={note.structured} />

          {note.safety_flags.length > 0 && (
            <div className="mt-4 rounded-xl border border-orange-200 bg-orange-50 p-3">
              <p className="flex items-center gap-1.5 text-sm font-semibold text-orange-900">
                <IconWarning className="h-4 w-4" aria-hidden="true" />
                Passage incertain — à vérifier
              </p>
              <ul className="mt-1 list-disc pl-5 text-xs text-orange-800">
                {note.safety_flags.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}

          {note.validation && (
            <div className="mt-4 rounded-xl border border-slate-200 bg-surface p-3">
              <p className="flex items-center gap-1.5 text-sm font-semibold text-ink">
                <IconCheckCircle className="h-4 w-4 text-primary" aria-hidden="true" />
                Vérification automatique du brouillon
              </p>
              {note.validation.issues.length === 0 ? (
                <p className="mt-1 text-xs text-muted">
                  Aucun point bloquant détecté. La validation reste humaine.
                </p>
              ) : (
                <ul className="mt-1.5 space-y-1">
                  {note.validation.issues.map((iss, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-muted">
                      <span className="badge-muted shrink-0">
                        {iss.code === "human_required" ? "À renseigner" : "À vérifier"}
                      </span>
                      {iss.message}
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-2 text-[11px] text-muted">
                La vérification n'ajoute ni ne corrige aucune donnée clinique.
              </p>
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
                  <IconCheckCircle className="h-4 w-4" aria-hidden="true" />
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
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 animate-check-pop items-center justify-center rounded-full bg-emerald-600 text-white">
              <IconCheck className="h-5 w-5" aria-hidden="true" />
            </span>
            <div>
              <p className="font-semibold text-emerald-800">Consultation validée</p>
              <p className="mt-0.5 text-sm text-emerald-700">
                La note est validée et historisée. Seul un professionnel peut valider une note.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  uncertain,
}: {
  label: string;
  value: string | null;
  uncertain: boolean;
}) {
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
      <Field
        label="Recommandations"
        value={note.recommendations.value}
        uncertain={note.recommendations.uncertain}
      />
      <Field label="Suivi" value={note.follow_up.value} uncertain={note.follow_up.uncertain} />
    </dl>
  );
}
