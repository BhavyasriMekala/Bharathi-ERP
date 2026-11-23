"""Bharathi bill submission, OCR, and verification workflow."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.bharathi_client import BILL_SUBMISSION_STATUSES
from app.core.permissions import get_role_names, user_is_admin
from app.models.bharathi import (
    BharathiBillExtraction,
    BharathiBillFile,
    BharathiBillSubmission,
    BharathiBillVerificationEvent,
)
from app.models.file_storage import StoredFile
from app.models.user import User
from app.services.audit_log_service import AuditLogService
from app.services.bharathi.ocr_providers import dumps_json, get_ocr_provider


def _roles(user: User) -> set[str]:
    return {r.strip() for r in get_role_names(user)}


def assert_supervisor_or_above(user: User) -> None:
    if user_is_admin(user):
        return
    roles = _roles(user)
    if "Supervisor" in roles or "Accountant" in roles:
        return
    raise HTTPException(403, "Supervisor, Accountant, or Admin role required")


def assert_accountant_or_admin(user: User) -> None:
    if user_is_admin(user) or "Accountant" in _roles(user):
        return
    raise HTTPException(403, "Accountant or Admin required")


def supervisor_scope_user_id(user: User) -> int | None:
    if user_is_admin(user) or "Accountant" in _roles(user):
        return None
    if "Supervisor" in _roles(user):
        return user.id
    raise HTTPException(403, "Not authorized for bill submissions")


def _validate_stored_file(db: Session, user: User, stored_file_id: int | None) -> StoredFile:
    if not stored_file_id:
        raise HTTPException(400, "stored_file_id is required for each bill attachment")
    row = db.get(StoredFile, stored_file_id)
    if not row or row.tenant_id != user.tenant_id:
        raise HTTPException(404, "Stored file not found")
    if row.upload_status != "UPLOADED":
        raise HTTPException(400, "File upload is not complete")
    owner_only = supervisor_scope_user_id(user)
    if owner_only and row.uploaded_by_user_id not in (None, owner_only):
        raise HTTPException(403, "Cannot attach another user's file")
    return row


def _duplicate_check(db: Session, tenant_id: int, sha: str | None) -> int | None:
    if not sha:
        return None
    row = db.scalar(
        select(BharathiBillFile.submission_id)
        .where(BharathiBillFile.tenant_id == tenant_id, BharathiBillFile.content_sha256 == sha)
        .limit(1)
    )
    return int(row) if row else None


def create_submission(db: Session, user: User, payload: dict) -> BharathiBillSubmission:
    assert_supervisor_or_above(user)
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(400, "Tenant required")

    idem = (payload.get("idempotency_key") or "").strip()
    if idem:
        existing = db.scalar(
            select(BharathiBillSubmission).where(
                BharathiBillSubmission.tenant_id == tenant_id,
                BharathiBillSubmission.idempotency_key == idem,
            )
        )
        if existing:
            return existing

    sub = BharathiBillSubmission(
        tenant_id=tenant_id,
        submitted_by_user_id=user.id,
        status="DRAFT",
        vendor_hint=(payload.get("vendor_hint") or "").strip() or None,
        remarks=(payload.get("remarks") or "").strip() or None,
        idempotency_key=idem or None,
    )
    db.add(sub)
    db.flush()

    files = payload.get("files") or []
    if not files:
        raise HTTPException(400, "At least one file attachment is required")
    dup_id = None
    for f in files:
        stored = _validate_stored_file(db, user, f.get("stored_file_id"))
        sha = (stored.checksum_sha256 or f.get("content_sha256") or "").strip() or None
        if not sha and stored.original_filename:
            sha = hashlib.sha256(stored.original_filename.encode()).hexdigest()
        found = _duplicate_check(db, tenant_id, sha)
        if found and found != sub.id:
            dup_id = found
        db.add(
            BharathiBillFile(
                tenant_id=tenant_id,
                submission_id=sub.id,
                stored_file_id=stored.id,
                original_filename=stored.original_filename,
                mime_type=stored.mime_type or f.get("mime_type") or "application/octet-stream",
                file_size_bytes=int(stored.file_size or f.get("file_size_bytes") or 0),
                content_sha256=sha,
            )
        )
    if dup_id:
        sub.duplicate_of_id = dup_id
    db.flush()
    AuditLogService.log(
        db=db,
        current_user=user,
        action="bharathi.bill.create",
        module_name="bharathi_bills",
        resource="bharathi_bill_submission",
        resource_id=sub.id,
        details=f"status={sub.status}",
        commit=False,
    )
    db.commit()
    db.refresh(sub)
    return sub


def submit_for_processing(db: Session, user: User, submission_id: int, provider: str = "mock") -> BharathiBillSubmission:
    assert_supervisor_or_above(user)
    sub = _get_submission(db, user, submission_id)
    owner_only = supervisor_scope_user_id(user)
    if owner_only and sub.submitted_by_user_id != owner_only:
        raise HTTPException(403, "Supervisors may only submit own bills")
    if sub.status not in ("DRAFT", "REJECTED"):
        raise HTTPException(400, f"Cannot submit from status {sub.status}")
    sub.status = "SUBMITTED"
    sub.submitted_at = datetime.now(timezone.utc)
    db.flush()
    run_ocr(db, user, sub, provider=provider)
    sub.status = "PENDING_VERIFICATION"
    db.commit()
    db.refresh(sub)
    return sub


def run_ocr(db: Session, user: User, sub: BharathiBillSubmission, provider: str = "mock") -> BharathiBillExtraction:
    sub.status = "OCR_PROCESSING"
    db.flush()
    ocr = get_ocr_provider(provider)
    extracted, confidence = ocr.extract_invoice(
        filename=sub.vendor_hint or f"submission-{sub.id}",
        mime_type="image/jpeg",
        hints={"vendor_hint": sub.vendor_hint},
    )
    row = BharathiBillExtraction(
        tenant_id=sub.tenant_id,
        submission_id=sub.id,
        provider=provider if provider != "mock" else "mock",
        status="complete",
        extracted_json=dumps_json(extracted),
        confidence_json=dumps_json(confidence),
    )
    db.add(row)
    db.flush()
    return row


def verify_submission(db: Session, user: User, submission_id: int, action: str, comment: str | None, corrected: dict | None):
    assert_accountant_or_admin(user)
    sub = _get_submission(db, user, submission_id, allow_all=True)
    if sub.status not in ("PENDING_VERIFICATION", "OCR_PROCESSING", "SUBMITTED"):
        raise HTTPException(400, "Not in verification queue")
    act = action.strip().lower()
    if act == "verify":
        sub.status = "VERIFIED"
        sub.verified_by_user_id = user.id
        sub.verified_at = datetime.now(timezone.utc)
    elif act == "reject":
        sub.status = "REJECTED"
    elif act in ("request_correction", "correction"):
        sub.status = "DRAFT"
    else:
        raise HTTPException(400, "Invalid action")
    db.add(
        BharathiBillVerificationEvent(
            tenant_id=sub.tenant_id,
            submission_id=sub.id,
            actor_user_id=user.id,
            action=act,
            comment=comment,
            payload_json=json.dumps(corrected) if corrected else None,
        )
    )
    if corrected:
        ext = db.scalar(
            select(BharathiBillExtraction)
            .where(BharathiBillExtraction.submission_id == sub.id)
            .order_by(BharathiBillExtraction.id.desc())
            .limit(1)
        )
        if ext and ext.extracted_json:
            data = json.loads(ext.extracted_json)
            data.update(corrected)
            ext.extracted_json = dumps_json(data)
    db.commit()
    db.refresh(sub)
    return sub


def list_submissions(db: Session, user: User, status: str | None = None) -> list[BharathiBillSubmission]:
    assert_supervisor_or_above(user)
    tenant_id = user.tenant_id
    q = select(BharathiBillSubmission).where(BharathiBillSubmission.tenant_id == tenant_id)
    owner = supervisor_scope_user_id(user)
    if owner:
        q = q.where(BharathiBillSubmission.submitted_by_user_id == owner)
    if status:
        q = q.where(BharathiBillSubmission.status == status)
    return list(db.scalars(q.order_by(BharathiBillSubmission.id.desc())).all())


def _get_submission(db: Session, user: User, submission_id: int, allow_all: bool = False) -> BharathiBillSubmission:
    tenant_id = user.tenant_id
    sub = db.get(BharathiBillSubmission, submission_id)
    if not sub or sub.tenant_id != tenant_id:
        raise HTTPException(404, "Submission not found")
    if not allow_all:
        owner = supervisor_scope_user_id(user)
        if owner and sub.submitted_by_user_id != owner:
            raise HTTPException(403, "Forbidden")
    return sub


def submission_to_dict(db: Session, sub: BharathiBillSubmission) -> dict:
    files = db.scalars(select(BharathiBillFile).where(BharathiBillFile.submission_id == sub.id)).all()
    ext = db.scalar(
        select(BharathiBillExtraction)
        .where(BharathiBillExtraction.submission_id == sub.id)
        .order_by(BharathiBillExtraction.id.desc())
        .limit(1)
    )
    latest = None
    if ext:
        latest = {
            "id": ext.id,
            "provider": ext.provider,
            "status": ext.status,
            "extracted": json.loads(ext.extracted_json) if ext.extracted_json else None,
            "confidence": json.loads(ext.confidence_json) if ext.confidence_json else None,
            "error_message": ext.error_message,
        }
    if sub.status not in BILL_SUBMISSION_STATUSES:
        pass
    return {
        "id": sub.id,
        "status": sub.status,
        "vendor_hint": sub.vendor_hint,
        "remarks": sub.remarks,
        "submitted_by_user_id": sub.submitted_by_user_id,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        "duplicate_of_id": sub.duplicate_of_id,
        "files": [
            {
                "id": f.id,
                "original_filename": f.original_filename,
                "mime_type": f.mime_type,
                "stored_file_id": f.stored_file_id,
            }
            for f in files
        ],
        "latest_extraction": latest,
    }