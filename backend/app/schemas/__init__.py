"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---- Auth ----
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    phone: str | None = None
    role: str = "patient"
    organization_name: str | None = None
    profession: str | None = None
    specialty: str | None = None
    license_number: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    organization_id: str | None = None
    is_demo: bool = False

    class Config:
        from_attributes = True


class MeOut(UserOut):
    professional: ProfessionalOut | None = None


class ProfessionalOut(BaseModel):
    id: str
    profession: str
    specialty: str | None = None
    license_number: str | None = None
    verification_status: str
    is_demo: bool = False

    class Config:
        from_attributes = True


# ---- Patients ----
class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: datetime | None = None
    sex: str | None = None
    phone: str | None = None
    region: str | None = None


class PatientOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    date_of_birth: datetime | None = None
    sex: str | None = None
    phone: str | None = None
    region: str | None = None
    is_demo: bool = False

    class Config:
        from_attributes = True


# ---- Consultations ----
class ConsultationCreate(BaseModel):
    patient_id: str
    chief_complaint: str | None = None


class ConsultationOut(BaseModel):
    id: str
    patient_id: str
    professional_id: str
    status: str
    chief_complaint: str | None = None
    version: int
    validated_by: str | None = None
    validated_at: datetime | None = None
    is_demo: bool = False

    class Config:
        from_attributes = True


class ValidateRequest(BaseModel):
    chief_complaint: str | None = None
    decision: str | None = None
    follow_up: str | None = None
    change_note: str | None = None


# ---- Scribe / AI ----
class TranscribeRequest(BaseModel):
    consultation_id: str
    language_hint: str = "wolof"
    text_hint: str | None = None
    consent_audio: bool = False
    audio_base64: str | None = None


class StructureRequest(BaseModel):
    transcription_id: str


class StructuredFieldOut(BaseModel):
    value: str | None = None
    uncertain: bool = False
    source_span: str | None = None


# ---- Documents ----
class DocumentCreate(BaseModel):
    patient_id: str | None = None
    consultation_id: str | None = None
    doc_type: str
    title: str
    content: str = ""


# ---- Teleconsultation ----
class TeleconsultationCreate(BaseModel):
    patient_id: str
    scheduled_at: datetime | None = None
    reason: str | None = None


# ---- Messages ----
class MessageCreate(BaseModel):
    recipient_id: str
    body: str
    patient_id: str | None = None


# ---- Coordination ----
class ReferralCreate(BaseModel):
    patient_id: str
    to_user_id: str | None = None
    to_org_id: str | None = None
    reason: str
    priority: str = "normal"


# ---- Consent ----
class ConsentCreate(BaseModel):
    patient_id: str
    scope: str
    granted: bool
    grantee_id: str | None = None
    document_ref: str | None = None


# ---- Break glass ----
class BreakGlassRequest(BaseModel):
    patient_id: str
    reason: str
    duration_minutes: int = 60


# ---- Billing ----
class SubscribeRequest(BaseModel):
    plan_code: str


class PaymentRequest(BaseModel):
    subscription_id: str
    provider: str


# ---- Verification ----
class VerificationDecision(BaseModel):
    status: str  # in_review | verified | refused | to_complete
    notes: str | None = None


TokenResponse.model_rebuild()
MeOut.model_rebuild()
