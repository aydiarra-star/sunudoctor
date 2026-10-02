"""SQLAlchemy entities for SunuDoctor.

Design principles:
- Clinical data (encounters, observations, consultations, notes) is strictly
  separated from billing data (subscriptions, payments).
- Every record that could be synthetic carries an ``is_demo`` flag so demo
  content is always distinguishable from real content.
- Uncertainty is first-class: ``is_uncertain`` flags mark values that must be
  verified by a human, never presented as confirmed facts.
"""
from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(str, enum.Enum):
    patient = "patient"
    doctor = "doctor"
    nurse = "nurse"
    midwife = "midwife"
    other_professional = "other_professional"
    community_agent = "community_agent"
    social_worker = "social_worker"
    org_admin = "org_admin"
    platform_admin = "platform_admin"


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    in_review = "in_review"
    verified = "verified"
    refused = "refused"
    to_complete = "to_complete"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.patient)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    organization: Mapped[Organization | None] = relationship(back_populates="members")
    professional: Mapped[Professional | None] = relationship(back_populates="user")


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(64), default="cabinet")
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    members: Mapped[list[User]] = relationship(back_populates="organization")


class Professional(Base, TimestampMixin):
    __tablename__ = "professionals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    profession: Mapped[str] = mapped_column(String(64))
    specialty: Mapped[str | None] = mapped_column(String(128), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    license_authority: Mapped[str | None] = mapped_column(String(128), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), default=VerificationStatus.pending
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="professional")


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    first_name: Mapped[str] = mapped_column(String(128))
    last_name: Mapped[str] = mapped_column(String(128))
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    national_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class CareTeamAccess(Base, TimestampMixin):
    """Explicit, scoped grant of access to a patient record (RBAC resource level)."""

    __tablename__ = "care_team_access"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    level: Mapped[str] = mapped_column(String(16), default="view")  # view | edit | full
    granted_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Encounter(Base, TimestampMixin):
    __tablename__ = "encounters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    professional_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    encounter_type: Mapped[str] = mapped_column(String(32), default="consultation")
    status: Mapped[str] = mapped_column(String(32), default="open")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Consultation(Base, TimestampMixin):
    __tablename__ = "consultations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    encounter_id: Mapped[str | None] = mapped_column(ForeignKey("encounters.id"), nullable=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    professional_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up: Mapped[str | None] = mapped_column(Text, nullable=True)
    validated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class NoteVersion(Base, TimestampMixin):
    """Immutable history of a consultation note. Enables versioning/audit."""

    __tablename__ = "note_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    consultation_id: Mapped[str] = mapped_column(ForeignKey("consultations.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    content_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    change_note: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Observation(Base, TimestampMixin):
    """Vitals and clinical observations. Uncertainty is explicit."""

    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    encounter_id: Mapped[str | None] = mapped_column(ForeignKey("encounters.id"), nullable=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(128))
    value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_uncertain: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(32), default="manual")  # manual | ai | device
    recorded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Allergy(Base, TimestampMixin):
    __tablename__ = "allergies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    substance: Mapped[str] = mapped_column(String(128))
    reaction: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_uncertain: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(32), default="manual")
    recorded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class Medication(Base, TimestampMixin):
    __tablename__ = "medications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    encounter_id: Mapped[str | None] = mapped_column(ForeignKey("encounters.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(128))
    dose: Mapped[str | None] = mapped_column(String(64), nullable=True)
    route: Mapped[str | None] = mapped_column(String(64), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_uncertain: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(32), default="manual")
    prescribed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    encounter_id: Mapped[str | None] = mapped_column(ForeignKey("encounters.id"), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(32))  # report | prescription | letter ...
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Appointment(Base, TimestampMixin):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    professional_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="requested")
    channel: Mapped[str] = mapped_column(String(32), default="in_person")
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class Teleconsultation(Base, TimestampMixin):
    __tablename__ = "teleconsultations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    appointment_id: Mapped[str | None] = mapped_column(
        ForeignKey("appointments.id"), nullable=True
    )
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    professional_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), default="requested")
    provider: Mapped[str] = mapped_column(String(32), default="none")  # none | webrtc
    room_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    report: Mapped[str | None] = mapped_column(Text, nullable=True)


class SignalingMessage(Base):
    """Short-lived WebRTC signalling envelope (offer/answer/ICE candidate).

    Messages are scoped to a room, expire quickly, and are only readable by
    participants authorized for that room. This is a minimal, self-hosted
    signalling store; no media ever transits the server.
    """

    __tablename__ = "signaling_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    room_ref: Mapped[str] = mapped_column(String(64), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(16))  # offer | answer | candidate | bye
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    thread_id: Mapped[str] = mapped_column(String(64), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    patient_id: Mapped[str | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Referral(Base, TimestampMixin):
    __tablename__ = "referrals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    from_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    to_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    from_org_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    to_org_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    status: Mapped[str] = mapped_column(String(32), default="created")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Consent(Base, TimestampMixin):
    __tablename__ = "consents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    grantee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    scope: Mapped[str] = mapped_column(String(32))  # access|share|teleconsultation|audio|ai|research
    granted: Mapped[bool] = mapped_column(Boolean, default=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    document_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    plan_code: Mapped[str] = mapped_column(String(64))
    plan_label: Mapped[str] = mapped_column(String(128))
    price_fcfa: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="trial")
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Payment(Base, TimestampMixin):
    """Billing data. Never influences clinical records."""

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    subscription_id: Mapped[str | None] = mapped_column(
        ForeignKey("subscriptions.id"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(32))  # wave | orange_money | card | bank
    provider_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    amount_fcfa: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="XOF")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WebhookEvent(Base):
    """Idempotent record of every provider webhook received.

    A webhook is processed at most once: the ``event_key`` (provider + event id)
    is unique. Replays are stored but ignored. This is what makes server-side
    confirmation trustworthy — a browser can never assert payment success.
    """

    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    event_key: Mapped[str] = mapped_column(String(191), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), default="")
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    patient_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class AITranscription(Base, TimestampMixin):
    __tablename__ = "ai_transcriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    consultation_id: Mapped[str] = mapped_column(ForeignKey("consultations.id"), index=True)
    audio_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(32), default="wolof")
    provider: Mapped[str] = mapped_column(String(32), default="demo")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_audio: Mapped[bool] = mapped_column(Boolean, default=False)


class AIStructuredNote(Base, TimestampMixin):
    __tablename__ = "ai_structured_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    consultation_id: Mapped[str] = mapped_column(ForeignKey("consultations.id"), index=True)
    transcription_id: Mapped[str | None] = mapped_column(
        ForeignKey("ai_transcriptions.id"), nullable=True
    )
    structured_json: Mapped[str] = mapped_column(Text, default="{}")
    safety_flags_json: Mapped[str] = mapped_column(Text, default="[]")
    model: Mapped[str] = mapped_column(String(64), default="demo")
    status: Mapped[str] = mapped_column(String(32), default="draft_ai")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    validated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, default="")
    notif_type: Mapped[str] = mapped_column(String(32), default="info")
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class BreakGlassEvent(Base):
    __tablename__ = "break_glass_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    reason: Mapped[str] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    audit_log_id: Mapped[str | None] = mapped_column(ForeignKey("audit_logs.id"), nullable=True)


class VerificationRequest(Base, TimestampMixin):
    __tablename__ = "verification_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    professional_id: Mapped[str] = mapped_column(ForeignKey("professionals.id"), index=True)
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), default=VerificationStatus.pending
    )
    documents_json: Mapped[str] = mapped_column(Text, default="[]")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SupportTicket(Base, TimestampMixin):
    """Support requests raised by users. Contains no clinical content."""

    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    requester_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(32), default="general")
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
