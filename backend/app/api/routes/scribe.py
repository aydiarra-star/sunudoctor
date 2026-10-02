"""Clinical Scribe: the core pipeline.

PARLER -> TRANSCRIRE -> STRUCTURER -> VÉRIFIER -> VALIDER

Nothing produced by the AI is ever presented as validated. A generated note is
always labelled "BROUILLON IA" until a professional explicitly validates it.
Original audio/transcript are retained only when consent allows.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_client_meta,
    get_current_user,
    require_verified_professional,
)
from app.core.database import get_db
from app.core.rbac import can_access_patient
from app.models.entities import (
    AIStructuredNote,
    AITranscription,
    Consultation,
    NoteVersion,
    Patient,
    Role,
    User,
)
from app.schemas import (
    ConsultationCreate,
    ConsultationOut,
    StructureRequest,
    TranscribeRequest,
    ValidateRequest,
)
from app.services import audit
from app.services.ai.factory import (
    get_ai_validation_provider,
    get_clinical_ai_provider,
    get_language_detection_provider,
    get_safety_provider,
    get_stt_provider,
)
from app.services.ai.real_providers import ProviderUnavailable

router = APIRouter(prefix="/scribe", tags=["scribe"])

CLINICAL_WRITERS = {
    Role.doctor,
    Role.nurse,
    Role.midwife,
    Role.other_professional,
    Role.community_agent,
    Role.social_worker,
}


def _consultation_for(db: Session, user: User, consultation_id: str) -> Consultation:
    cons = db.get(Consultation, consultation_id)
    if cons is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consultation introuvable")
    if not can_access_patient(db, user, cons.patient_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès non autorisé à cette consultation")
    return cons


@router.post("/consultations", response_model=ConsultationOut, status_code=201)
def create_consultation(
    payload: ConsultationCreate,
    user: User = Depends(require_verified_professional),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    if user.role not in CLINICAL_WRITERS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle non autorisé")
    if db.get(Patient, payload.patient_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient introuvable")
    if not can_access_patient(db, user, payload.patient_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès non autorisé à ce patient")
    cons = Consultation(
        patient_id=payload.patient_id,
        professional_id=user.id,
        chief_complaint=payload.chief_complaint,
        status="draft",
    )
    db.add(cons)
    db.commit()
    db.refresh(cons)
    audit.log_action(
        db,
        action=audit.AuditAction.CONSULTATION_CREATE,
        actor=user,
        resource_type="consultation",
        resource_id=cons.id,
        patient_id=cons.patient_id,
        ip=meta.get("ip"),
    )
    return cons


@router.get("/consultations/{consultation_id}", response_model=ConsultationOut)
def get_consultation(
    consultation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _consultation_for(db, user, consultation_id)


@router.post("/transcribe")
def transcribe(
    payload: TranscribeRequest,
    user: User = Depends(require_verified_professional),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    """Step 1-2: record + transcribe. Audio is retained only with consent."""
    cons = _consultation_for(db, user, payload.consultation_id)
    if user.role not in CLINICAL_WRITERS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle non autorisé")

    audio = None
    if payload.audio_base64:
        import base64

        try:
            audio = base64.b64decode(payload.audio_base64)
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Audio invalide") from None

    provider, is_demo = get_stt_provider()
    try:
        result = provider.transcribe(
            audio, language_hint=payload.language_hint, text_hint=payload.text_hint
        )
    except ProviderUnavailable as exc:
        # A real STT engine is configured but unreachable: degrade honestly.
        # We never fabricate a transcript.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Service de transcription temporairement indisponible. {exc}",
        ) from exc

    # Detect the actual language mix without ever rewriting the transcript.
    detector, detection_is_demo = get_language_detection_provider()
    detection = detector.detect(result.raw_text) if result.raw_text else None

    transcription = AITranscription(
        consultation_id=cons.id,
        raw_text=result.raw_text,
        language=(detection.primary if detection else result.language),
        provider=result.provider,
        is_demo=is_demo,
        consent_audio=payload.consent_audio,
        # Audio reference is only stored when consent is granted.
        audio_ref="retained" if (payload.consent_audio and audio) else None,
    )
    db.add(transcription)
    db.commit()
    db.refresh(transcription)

    audit.log_action(
        db,
        action=audit.AuditAction.AI_TRANSCRIBE,
        actor=user,
        resource_type="consultation",
        resource_id=cons.id,
        patient_id=cons.patient_id,
        meta={"provider": result.provider, "is_demo": is_demo, "consent_audio": payload.consent_audio},
        ip=meta.get("ip"),
    )

    return {
        "transcription_id": transcription.id,
        "raw_text": result.raw_text,
        "language": transcription.language,
        "provider": result.provider,
        "is_demo": is_demo,
        "demo_banner": "Mode démonstration" if is_demo else None,
        "uncertain_spans": result.uncertain_spans,
        "confidence": result.confidence,
        "duration_seconds": result.duration_seconds,
        "segments": [
            {
                "start": s.start,
                "end": s.end,
                "text": s.text,
                "language": s.language,
                "confidence": s.confidence,
            }
            for s in result.segments
        ],
        "audio_retained": transcription.audio_ref is not None,
        "detection": (
            {
                "primary": detection.primary,
                "languages": detection.languages,
                "mixed": detection.mixed,
                "confidence": detection.confidence,
                "is_demo": detection_is_demo,
            }
            if detection
            else None
        ),
    }


@router.post("/structure")
def structure(
    payload: StructureRequest,
    user: User = Depends(require_verified_professional),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    """Step 3-4: structure + safety verification. Output is a DRAFT only."""
    transcription = db.get(AITranscription, payload.transcription_id)
    if transcription is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transcription introuvable")
    cons = _consultation_for(db, user, transcription.consultation_id)
    if user.role not in CLINICAL_WRITERS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle non autorisé")

    provider, is_demo = get_clinical_ai_provider()
    try:
        note = provider.structure(transcription.raw_text, language=transcription.language)
    except ProviderUnavailable as exc:
        # The clinical AI is unreachable. The transcript is preserved and the
        # API says so plainly — it never invents a note.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Analyse clinique indisponible — transcription disponible. "
            f"Vous pouvez saisir la note manuellement. ({exc})",
        ) from exc

    safety_provider = get_safety_provider()
    note, flags = safety_provider.review(note, transcription.raw_text)

    # Automated draft review — reports issues only, never edits the note.
    validator, validation_is_demo = get_ai_validation_provider()
    validation = validator.validate(note, transcription.raw_text)

    structured = AIStructuredNote(
        consultation_id=cons.id,
        transcription_id=transcription.id,
        structured_json=json.dumps(note.to_dict(), ensure_ascii=False),
        safety_flags_json=json.dumps(flags, ensure_ascii=False),
        model=note.model,
        status="draft_ai",
        is_demo=is_demo,
    )
    db.add(structured)
    db.commit()
    db.refresh(structured)

    audit.log_action(
        db,
        action=audit.AuditAction.AI_STRUCTURE,
        actor=user,
        resource_type="consultation",
        resource_id=cons.id,
        patient_id=cons.patient_id,
        meta={"is_demo": is_demo, "flags": len(flags)},
        ip=meta.get("ip"),
    )

    return {
        "structured_note_id": structured.id,
        "status": "draft_ai",
        "disclaimer": (
            "Cette note a été générée avec l'aide de l'IA. Vérifiez son exactitude "
            "avant validation."
        ),
        "is_demo": is_demo,
        "demo_banner": "Mode démonstration" if is_demo else None,
        "structured": note.to_dict(),
        "safety_flags": flags,
        "uncertainties": note.uncertainties,
        "validation": {
            "ok": validation.ok,
            "is_demo": validation_is_demo,
            "issues": [
                {"field": i.field, "code": i.code, "message": i.message} for i in validation.issues
            ],
        },
    }


@router.post("/consultations/{consultation_id}/validate", response_model=ConsultationOut)
def validate_consultation(
    consultation_id: str,
    payload: ValidateRequest,
    user: User = Depends(require_verified_professional),
    db: Session = Depends(get_db),
    meta: dict = Depends(get_client_meta),
):
    """Step 5: professional validation. Only a human can validate a note."""
    cons = _consultation_for(db, user, consultation_id)
    if user.role not in CLINICAL_WRITERS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Seul un professionnel peut valider")

    if payload.chief_complaint is not None:
        cons.chief_complaint = payload.chief_complaint
    if payload.decision is not None:
        cons.decision = payload.decision
    if payload.follow_up is not None:
        cons.follow_up = payload.follow_up

    cons.version += 1
    cons.status = "validated"
    cons.validated_by = user.id
    cons.validated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    db.add(
        NoteVersion(
            consultation_id=cons.id,
            version=cons.version,
            content_json=json.dumps(
                {
                    "chief_complaint": cons.chief_complaint,
                    "decision": cons.decision,
                    "follow_up": cons.follow_up,
                },
                ensure_ascii=False,
            ),
            created_by=user.id,
            change_note=payload.change_note or "Validation par le professionnel",
        )
    )
    # Mark the latest AI note as validated (never before this point).
    latest = (
        db.query(AIStructuredNote)
        .filter(AIStructuredNote.consultation_id == cons.id)
        .order_by(AIStructuredNote.created_at.desc())
        .first()
    )
    if latest:
        latest.status = "validated"
        latest.validated_by = user.id
        latest.validated_at = cons.validated_at

    db.commit()
    db.refresh(cons)

    audit.log_action(
        db,
        action=audit.AuditAction.CONSULTATION_VALIDATE,
        actor=user,
        resource_type="consultation",
        resource_id=cons.id,
        patient_id=cons.patient_id,
        meta={"version": cons.version},
        ip=meta.get("ip"),
    )
    return cons


@router.get("/consultations/{consultation_id}/history")
def history(
    consultation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _consultation_for(db, user, consultation_id)
    versions = (
        db.query(NoteVersion)
        .filter(NoteVersion.consultation_id == consultation_id)
        .order_by(NoteVersion.version.desc())
        .all()
    )
    return [
        {
            "version": v.version,
            "created_by": v.created_by,
            "created_at": v.created_at,
            "change_note": v.change_note,
            "content": json.loads(v.content_json),
        }
        for v in versions
    ]


@router.get("/wolof-eval")
def wolof_eval():
    """Expose the Wolof/clinical safety evaluation cases for the UI/docs.

    These cases document what the pipeline guarantees and where its limits are.
    """
    from app.services.ai.eval_cases import CASES

    return {
        "count": len(CASES),
        "cases": CASES,
        "note": "Suite d'évaluation — la transcription réelle en wolof requiert un "
        "moteur STT dédié non configuré en mode démonstration.",
    }
