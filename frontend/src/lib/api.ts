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
    is_demo: boolean;
  } | null;
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
