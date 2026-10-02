/**
 * Typed API client.
 *
 * The base URL is configurable at build time via VITE_API_BASE. When the
 * frontend is deployed to GitHub Pages without a backend, calls fail and the UI
 * must surface an explicit "backend non connecté" state rather than pretending
 * to work.
 */
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("sd_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init.headers ?? {}),
    },
  });
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail =
      body && typeof body.detail === "string"
        ? body.detail
        : `Erreur ${res.status}`;
    throw new ApiError(detail, res.status);
  }
  return body as T;
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(p: string) => request<T>(p, { method: "DELETE" }),
};

export type Capability = "demo" | "live" | "non_connecte" | "configuration_requise" | "partiel";

export interface ProviderInfo {
  requested: string;
  connected: boolean;
  provider: string;
  reason: string;
  model?: string;
}

export interface Meta {
  app: string;
  ai_mode: "demo" | "live";
  payment_mode: "demo" | "live";
  demo_banner: string | null;
  providers?: Record<string, ProviderInfo>;
  capabilities: Record<string, Capability>;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization_id: string | null;
  is_demo: boolean;
  professional?: {
    id: string;
    profession: string;
    specialty: string | null;
    license_number: string | null;
    verification_status: string;
    verification_level: string;
    badge?: VerificationBadge | null;
    access_tier: string;
    is_demo: boolean;
  } | null;
}

export interface VerificationBadge {
  level: string;
  label: string;
  tone: "success" | "info" | "warning" | "danger" | "neutral";
  verified_by: string | null;
  note?: string;
}

export interface Facility {
  id: string;
  name: string;
  short_name: string | null;
  type: string;
  type_label: string;
  region: string | null;
  district: string | null;
  commune: string | null;
  address: string | null;
  official_id: string | null;
  source: string;
  source_type: string;
  status: string;
  status_label: string;
  is_demo: boolean;
  match_score?: number;
  match_outcome?: string;
  notice?: string;
}

export interface Affiliation {
  id: string;
  facility_id: string;
  status: string;
  requested_at: string;
  decided_at: string | null;
  ended_at: string | null;
  role_function?: string | null;
}

export interface MyVerification {
  professional_id: string;
  verification_status: string;
  verification_level: string;
  level_label: string;
  badge: VerificationBadge;
  access_tier: string;
  can_author_clinical: boolean;
  review_notes: string | null;
  message: string;
  affiliations: Affiliation[];
  documents_received?: number;
  duplicates_flagged?: number;
}

export interface QueueEntry {
  professional_id: string;
  full_name: string | null;
  profession: string | null;
  specialty: string | null;
  license_number: string | null;
  verification_level: string;
  submitted_at: string;
  documents_submitted: number;
  is_self: boolean;
  match: {
    outcome: string;
    score: number;
    definitive: boolean;
    requires_human_review: boolean;
    reasons: string[];
    source_note: string;
    source_consulted: string | null;
  };
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string | null;
  sex: string | null;
  phone: string | null;
  region: string | null;
  is_demo: boolean;
}

export interface Consultation {
  id: string;
  patient_id: string;
  professional_id: string;
  status: string;
  chief_complaint: string | null;
  version: number;
  validated_by: string | null;
  validated_at: string | null;
  is_demo: boolean;
}

export interface StructuredField {
  value: string | null;
  uncertain: boolean;
  source_span: string | null;
}

export interface LanguageDetection {
  primary: string;
  languages: string[];
  mixed: boolean;
  confidence: number;
  is_demo: boolean;
}

export interface ValidationIssue {
  field: string;
  code: string;
  message: string;
}

export interface DraftValidation {
  ok: boolean;
  is_demo: boolean;
  issues: ValidationIssue[];
}

export interface StructuredNote {
  chief_complaint: StructuredField;
  history: StructuredField;
  symptoms: StructuredField[];
  negated_symptoms: string[];
  history_items: StructuredField[];
  allergies: StructuredField[];
  medications: Array<{ name: string; dose: string | null; uncertain: boolean }>;
  vitals: Array<{ label: string; value: string; unit: string | null }>;
  exam: StructuredField;
  investigations: StructuredField;
  diagnosis: StructuredField;
  decision: StructuredField;
  prescription: StructuredField;
  recommendations: StructuredField;
  follow_up: StructuredField;
  uncertainties: string[];
  provider: string;
  is_demo: boolean;
  model: string;
}
