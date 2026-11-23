"""OCR processing, line persistence, approval transitions."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.bharathi_client import BILL_SUBMISSION_STATUSES
from app.models.bharathi import (
    BharathiBillExtraction,
    BharathiBillFile,
    BharathiBillOcrJob,
    BharathiBillSubmission,
    BharathiBillVerificationEvent,
    BharathiPurchaseInvoiceLine,
)
from app.models.file_storage import StoredFile
from app.models.user import User
from app.services.bharathi.duplicate_detection import (
    assess_duplicate,
    norm_invoice_number,
    supplier_identity_key,
)
from app.services.bharathi.file_bytes_loader import load_stored_file_bytes
from app.services.bharathi.invoice_extraction_schema import parse_extraction_payload
from app.services.bharathi.invoice_validation import validate_extraction, warnings_need_review
from app.services.bharathi.ocr_providers import dumps_json, get_ocr_provider, resolve_provider_name


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def assert_can_approve(user: User) -> None:
    from app.core.permissions import get_role_names, user_is_admin

    if user_is_admin(user):
        return
    if "Accountant" in get_role_names(user):
        return
    raise HTTPException(403, "Accountant or Admin required to approve invoices")


def apply_extraction_to_submission(db: Session, sub: BharathiBillSubmission, data: dict) -> list[dict]:
    ext = parse_extraction_payload(data)
    warnings = validate_extraction(ext)
    sub.supplier_name = ext.supplier_name
    sub.supplier_gstin = ext.supplier_gstin
    sub.invoice_number = ext.invoice_number
    sub.invoice_number_norm = norm_invoice_number(ext.invoice_number)
    sub.supplier_identity_key = supplier_identity_key(
        gstin=ext.supplier_gstin,
        supplier_name=ext.supplier_name,
        vendor_hint=sub.vendor_hint,
    )
    sub.invoice_date = _parse_date(ext.invoice_date)
    sub.due_date = _parse_date(ext.due_date)
    sub.currency_code = (ext.currency or "INR")[:8]
    sub.grand_total = ext.grand_total
    sub.validation_warnings_json = json.dumps(warnings)
    sub.tally_sync_status = sub.tally_sync_status or "not_configured"
    db.execute(delete(BharathiPurchaseInvoiceLine).where(BharathiPurchaseInvoiceLine.submission_id == sub.id))
    for idx, line in enumerate(ext.line_items, start=1):
        db.add(
            BharathiPurchaseInvoiceLine(
                tenant_id=sub.tenant_id,
                submission_id=sub.id,
                line_number=idx,
                description=line.description,
                hsn_sac=line.hsn_sac,
                quantity=line.quantity,
                unit=line.unit,
                unit_price=line.unit_price,
                discount_amount=line.discount_amount,
                tax_rate=line.tax_rate,
                taxable_amount=line.taxable_amount,
                tax_amount=line.tax_amount,
                line_total=line.line_total,
            )
        )
    return warnings


def run_ocr(db: Session, user: User, sub: BharathiBillSubmission, provider: str | None = None) -> BharathiBillExtraction:
    provider_name = resolve_provider_name(provider)
    sub.status = "OCR_PROCESSING"
    job = BharathiBillOcrJob(
        tenant_id=sub.tenant_id,
        submission_id=sub.id,
        status="processing",
        provider=provider_name,
        attempts=1,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()
    bill_file = db.scalar(
        select(BharathiBillFile).where(BharathiBillFile.submission_id == sub.id).order_by(BharathiBillFile.id).limit(1)
    )
    if not bill_file or not bill_file.stored_file_id:
        job.status = "failed"
        job.error_message = "No stored file on submission"
        job.finished_at = datetime.now(timezone.utc)
        sub.status = "EXTRACTION_FAILED"
        row = BharathiBillExtraction(
            tenant_id=sub.tenant_id,
            submission_id=sub.id,
            provider=provider_name,
            status="failed",
            error_message=job.error_message,
        )
        db.add(row)
        return row
    stored = db.get(StoredFile, bill_file.stored_file_id)
    if not stored:
        job.status = "failed"
        job.error_message = "Stored file record missing"
        job.finished_at = datetime.now(timezone.utc)
        sub.status = "EXTRACTION_FAILED"
        row = BharathiBillExtraction(
            tenant_id=sub.tenant_id,
            submission_id=sub.id,
            provider=provider_name,
            status="failed",
            error_message=job.error_message,
        )
        db.add(row)
        return row
    try:
        file_bytes, mime = load_stored_file_bytes(db, stored)
        ocr = get_ocr_provider(provider_name)
        extracted, confidence = ocr.extract_invoice(
            filename=bill_file.original_filename,
            mime_type=mime,
            file_bytes=file_bytes,
            hints={"vendor_hint": sub.vendor_hint},
        )
        warnings = apply_extraction_to_submission(db, sub, extracted)
        dup = assess_duplicate(
            db,
            sub.tenant_id,
            file_sha=bill_file.content_sha256,
            supplier_key=sub.supplier_identity_key,
            invoice_number_norm=sub.invoice_number_norm,
            grand_total=sub.grand_total,
            invoice_date=sub.invoice_date,
            exclude_id=sub.id,
        )
        if dup.kind == "exact_business":
            sub.duplicate_of_id = dup.existing_submission_id
            sub.duplicate_status = "exact"
            sub.status = "DUPLICATE_REVIEW"
        elif dup.kind == "potential":
            sub.duplicate_of_id = dup.existing_submission_id
            sub.duplicate_status = "potential"
            sub.status = "DUPLICATE_REVIEW"
        elif dup.kind == "exact_file":
            sub.duplicate_of_id = dup.existing_submission_id
            sub.duplicate_status = "file"
        elif warnings_need_review(warnings):
            sub.status = "NEEDS_REVIEW"
        else:
            sub.status = "EXTRACTED"
        job.status = "complete"
        job.finished_at = datetime.now(timezone.utc)
        row = BharathiBillExtraction(
            tenant_id=sub.tenant_id,
            submission_id=sub.id,
            provider=provider_name,
            status="complete",
            extracted_json=dumps_json(extracted),
            confidence_json=dumps_json(confidence),
        )
        db.add(row)
        db.flush()
        return row
    except RuntimeError as exc:
        job.status = "failed"
        job.error_message = str(exc)[:2000]
        job.finished_at = datetime.now(timezone.utc)
        sub.status = "EXTRACTION_FAILED"
        row = BharathiBillExtraction(
            tenant_id=sub.tenant_id,
            submission_id=sub.id,
            provider=provider_name,
            status="failed",
            error_message=job.error_message,
        )
        db.add(row)
        return row
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)[:2000]
        job.finished_at = datetime.now(timezone.utc)
        sub.status = "EXTRACTION_FAILED"
        row = BharathiBillExtraction(
            tenant_id=sub.tenant_id,
            submission_id=sub.id,
            provider=provider_name,
            status="failed",
            error_message=job.error_message,
        )
        db.add(row)
        return row
    finally:
        _ = user


def finalize_after_ocr(db: Session, sub: BharathiBillSubmission) -> None:
    if sub.status in ("EXTRACTED", "NEEDS_REVIEW", "DUPLICATE_REVIEW"):
        sub.status = "PENDING_VERIFICATION"


def approve_submission(db: Session, user: User, submission_id: int, comment: str | None) -> BharathiBillSubmission:
    assert_can_approve(user)
    sub = db.scalar(
        select(BharathiBillSubmission)
        .where(
            BharathiBillSubmission.id == submission_id,
            BharathiBillSubmission.tenant_id == user.tenant_id,
        )
        .with_for_update()
    )
    if not sub:
        raise HTTPException(404, "Submission not found")
    if sub.status != "VERIFIED":
        raise HTTPException(400, "Invoice must be verified before approval")
    if sub.duplicate_status == "exact":
        raise HTTPException(409, detail="Cannot approve an exact duplicate invoice")
    sub.status = "APPROVED"
    sub.approved_by_user_id = user.id
    sub.approved_at = datetime.now(timezone.utc)
    sub.tally_sync_status = "not_synchronized"
    db.add(
        BharathiBillVerificationEvent(
            tenant_id=sub.tenant_id,
            submission_id=sub.id,
            actor_user_id=user.id,
            action="approve",
            comment=comment,
            payload_json=None,
        )
    )
    db.commit()
    db.refresh(sub)
    return sub


def list_submissions_paginated(
    db: Session,
    user: User,
    *,
    status: str | None,
    supplier: str | None,
    invoice_number: str | None,
    duplicate_status: str | None,
    offset: int,
    limit: int,
):
    from app.services.bharathi.bill_service import assert_supervisor_or_above, supervisor_scope_user_id

    assert_supervisor_or_above(user)
    q = select(BharathiBillSubmission).where(BharathiBillSubmission.tenant_id == user.tenant_id)
    owner = supervisor_scope_user_id(user)
    if owner:
        q = q.where(BharathiBillSubmission.submitted_by_user_id == owner)
    if status:
        q = q.where(BharathiBillSubmission.status == status)
    if supplier:
        like = f"%{supplier.strip()}%"
        q = q.where(
            (BharathiBillSubmission.supplier_name.ilike(like))
            | (BharathiBillSubmission.vendor_hint.ilike(like))
        )
    if invoice_number:
        norm = norm_invoice_number(invoice_number)
        q = q.where(
            (BharathiBillSubmission.invoice_number.ilike(f"%{invoice_number.strip()}%"))
            | (BharathiBillSubmission.invoice_number_norm == norm)
        )
    if duplicate_status:
        q = q.where(BharathiBillSubmission.duplicate_status == duplicate_status)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(db.scalars(q.order_by(BharathiBillSubmission.id.desc()).offset(offset).limit(limit)).all())
    return rows, int(total)


def list_verification_events(db: Session, tenant_id: int, submission_id: int) -> list[dict]:
    events = db.scalars(
        select(BharathiBillVerificationEvent)
        .where(
            BharathiBillVerificationEvent.tenant_id == tenant_id,
            BharathiBillVerificationEvent.submission_id == submission_id,
        )
        .order_by(BharathiBillVerificationEvent.id.desc())
    ).all()
    return [
        {
            "id": e.id,
            "action": e.action,
            "actor_user_id": e.actor_user_id,
            "comment": e.comment,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]