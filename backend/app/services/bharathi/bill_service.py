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
    BharathiPurchaseInvoiceLine,
)
from app.models.file_storage import StoredFile
from app.models.user import User
from app.services.audit_log_service import AuditLogService
from app.services.bharathi.invoice_workflow import finalize_after_ocr, run_ocr as run_ocr_job
from app.services.bharathi.ocr_providers import dumps_json, resolve_provider_name


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


def submit_for_processing(
    db: Session, user: User, submission_id: int, provider: str | None = None
) -> BharathiBillSubmission:
    assert_supervisor_or_above(user)
    sub = _get_submission(db, user, submission_id)
    owner_only = supervisor_scope_user_id(user)
    if owner_only and sub.submitted_by_user_id != owner_only:
        raise HTTPException(403, "Supervisors may only submit own bills")
    if sub.status not in ("DRAFT", "REJECTED", "EXTRACTION_FAILED"):
        raise HTTPException(400, f"Cannot submit from status {sub.status}")
    sub.status = "SUBMITTED"
    sub.submitted_at = datetime.now(timezone.utc)
    db.flush()
    resolved = resolve_provider_name(provider)
    if resolved == "unconfigured" and provider is None:
        sub.status = "EXTRACTION_FAILED"
        db.add(
            BharathiBillExtraction(
                tenant_id=sub.tenant_id,
                submission_id=sub.id,
                provider="unconfigured",
                status="failed",
                error_message="OCR is not configured. Upload saved; enter details manually when review is available.",
            )
        )
    else:
        run_ocr_job(db, user, sub, provider=provider)
        finalize_after_ocr(db, sub)
    db.commit()
    db.refresh(sub)
    return sub


def run_ocr(db: Session, user: User, sub: BharathiBillSubmission, provider: str | None = None) -> BharathiBillExtraction:
    row = run_ocr_job(db, user, sub, provider=provider)
    finalize_after_ocr(db, sub)
    return row


def verify_submission(
    db: Session,
    user: User,
    submission_id: int,
    action: str,
    comment: str | None,
    corrected: dict | None,
    corrected_line_items: list[dict] | None = None,
):
    assert_accountant_or_admin(user)
    sub = _get_submission(db, user, submission_id, allow_all=True)
    if sub.status not in (
        "PENDING_VERIFICATION",
        "NEEDS_REVIEW",
        "EXTRACTED",
        "DUPLICATE_REVIEW",
        "OCR_PROCESSING",
        "SUBMITTED",
    ):
        raise HTTPException(400, "Not in verification queue")
    act = action.strip().lower()
    if act in ("save_corrections", "correct"):
        act = "save_corrections"
    elif act == "verify":
        sub.status = "VERIFIED"
        sub.verified_by_user_id = user.id
        sub.verified_at = datetime.now(timezone.utc)
    elif act == "reject":
        sub.status = "REJECTED"
        sub.rejected_by_user_id = user.id
        sub.rejected_at = datetime.now(timezone.utc)
    elif act in ("request_correction", "correction"):
        sub.status = "DRAFT"
    else:
        raise HTTPException(400, "Invalid action")
    correction_payload: dict = {}
    if corrected:
        correction_payload["header"] = corrected
    if corrected_line_items:
        correction_payload["line_items"] = corrected_line_items
    db.add(
        BharathiBillVerificationEvent(
            tenant_id=sub.tenant_id,
            submission_id=sub.id,
            actor_user_id=user.id,
            action=act,
            comment=comment,
            payload_json=json.dumps(correction_payload) if correction_payload else None,
        )
    )
    if corrected or corrected_line_items:
        from app.services.bharathi.invoice_line_corrections import (
            apply_header_corrections,
            persist_corrected_line_items,
            validate_corrected_line_items,
        )

        prior = json.loads(sub.verified_fields_json) if sub.verified_fields_json else {}
        stored = {**prior}
        if corrected:
            apply_header_corrections(sub, corrected)
            stored["header"] = {**(stored.get("header") or {}), **corrected}
        if corrected_line_items:
            lines = validate_corrected_line_items([r for r in corrected_line_items])
            persist_corrected_line_items(db, sub, lines)
            stored["line_items"] = [ln.model_dump(mode="json") for ln in lines]
        sub.verified_fields_json = dumps_json(stored)
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
    lines = db.scalars(
        select(BharathiPurchaseInvoiceLine)
        .where(BharathiPurchaseInvoiceLine.submission_id == sub.id)
        .order_by(BharathiPurchaseInvoiceLine.line_number)
    ).all()
    warnings = json.loads(sub.validation_warnings_json) if sub.validation_warnings_json else []
    return {
        "id": sub.id,
        "status": sub.status,
        "vendor_hint": sub.vendor_hint,
        "remarks": sub.remarks,
        "submitted_by_user_id": sub.submitted_by_user_id,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        "duplicate_of_id": sub.duplicate_of_id,
        "duplicate_status": sub.duplicate_status,
        "supplier_name": sub.supplier_name,
        "supplier_gstin": sub.supplier_gstin,
        "invoice_number": sub.invoice_number,
        "invoice_date": sub.invoice_date.isoformat() if sub.invoice_date else None,
        "grand_total": float(sub.grand_total) if sub.grand_total is not None else None,
        "currency_code": sub.currency_code,
        "validation_warnings": warnings,
        "verified_at": sub.verified_at.isoformat() if sub.verified_at else None,
        "approved_at": sub.approved_at.isoformat() if sub.approved_at else None,
        "tally_sync_status": sub.tally_sync_status,
        "line_items": [
            {
                "id": li.id,
                "line_number": li.line_number,
                "description": li.description,
                "hsn_sac": li.hsn_sac,
                "quantity": float(li.quantity) if li.quantity is not None else None,
                "unit": li.unit,
                "unit_price": float(li.unit_price) if li.unit_price is not None else None,
                "discount_amount": float(li.discount_amount) if li.discount_amount is not None else None,
                "tax_rate": float(li.tax_rate) if li.tax_rate is not None else None,
                "taxable_amount": float(li.taxable_amount) if li.taxable_amount is not None else None,
                "tax_amount": float(li.tax_amount) if li.tax_amount is not None else None,
                "line_total": float(li.line_total) if li.line_total is not None else None,
            }
            for li in lines
        ],
        "verified_corrections": json.loads(sub.verified_fields_json) if sub.verified_fields_json else None,
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