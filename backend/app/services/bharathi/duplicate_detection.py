"""Supplier-scoped duplicate detection for Bharathi purchase invoices."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.bharathi import BharathiBillFile, BharathiBillSubmission

DuplicateKind = Literal["none", "exact_file", "exact_business", "potential"]

_BLOCKING_STATUSES = frozenset({
    "SUBMITTED",
    "OCR_PROCESSING",
    "EXTRACTED",
    "NEEDS_REVIEW",
    "PENDING_VERIFICATION",
    "VERIFIED",
    "APPROVED",
    "DUPLICATE_REVIEW",
    "SYNC_PENDING",
    "SYNCED",
})

_APPROVED_STATUSES = frozenset({"APPROVED", "SYNC_PENDING", "SYNCED"})


def norm_invoice_number(value: str | None) -> str | None:
    if not value:
        return None
    s = re.sub(r"\s+", "", str(value).strip().upper())
    return s or None


def supplier_identity_key(*, gstin: str | None, supplier_name: str | None, vendor_hint: str | None) -> str | None:
    g = (gstin or "").strip().upper()
    if g:
        return f"gstin:{g}"
    name = (supplier_name or vendor_hint or "").strip().lower()
    if not name:
        return None
    name = re.sub(r"[^a-z0-9]+", " ", name).strip()
    return f"name:{name}" if name else None


@dataclass(frozen=True, slots=True)
class DuplicateCheckResult:
    kind: DuplicateKind
    existing_submission_id: int | None = None
    message: str | None = None


def find_file_duplicate(db: Session, tenant_id: int, sha: str) -> int | None:
    if not sha:
        return None
    row = db.scalar(
        select(BharathiBillFile.submission_id)
        .where(BharathiBillFile.tenant_id == tenant_id, BharathiBillFile.content_sha256 == sha)
        .limit(1)
    )
    return int(row) if row else None


def find_business_duplicate(
    db: Session,
    tenant_id: int,
    supplier_key: str | None,
    invoice_number_norm: str | None,
    *,
    exclude_id: int | None = None,
) -> BharathiBillSubmission | None:
    if not supplier_key or not invoice_number_norm:
        return None
    q = select(BharathiBillSubmission).where(
        BharathiBillSubmission.tenant_id == tenant_id,
        BharathiBillSubmission.supplier_identity_key == supplier_key,
        BharathiBillSubmission.invoice_number_norm == invoice_number_norm,
        BharathiBillSubmission.status.in_(tuple(_BLOCKING_STATUSES)),
    )
    if exclude_id:
        q = q.where(BharathiBillSubmission.id != exclude_id)
    return db.scalars(q.limit(1)).first()


def find_potential_duplicate(
    db: Session,
    tenant_id: int,
    supplier_key: str | None,
    grand_total: Decimal | None,
    invoice_date,
    *,
    exclude_id: int | None = None,
) -> BharathiBillSubmission | None:
    if not supplier_key or grand_total is None or not invoice_date:
        return None
    tol = Decimal("1.00")
    q = select(BharathiBillSubmission).where(
        BharathiBillSubmission.tenant_id == tenant_id,
        BharathiBillSubmission.supplier_identity_key == supplier_key,
        BharathiBillSubmission.invoice_date == invoice_date,
        BharathiBillSubmission.grand_total.isnot(None),
        BharathiBillSubmission.status.in_(tuple(_BLOCKING_STATUSES)),
    )
    if exclude_id:
        q = q.where(BharathiBillSubmission.id != exclude_id)
    for row in db.scalars(q).all():
        if row.grand_total and abs(row.grand_total - grand_total) <= tol:
            if row.invoice_number_norm:
                continue
            return row
    return None


def assess_duplicate(
    db: Session,
    tenant_id: int,
    *,
    file_sha: str | None,
    supplier_key: str | None,
    invoice_number_norm: str | None,
    grand_total: Decimal | None,
    invoice_date,
    exclude_id: int | None = None,
) -> DuplicateCheckResult:
    file_dup = find_file_duplicate(db, tenant_id, file_sha or "")
    if file_dup and file_dup != exclude_id:
        existing = find_business_duplicate(
            db, tenant_id, supplier_key, invoice_number_norm, exclude_id=exclude_id
        )
        if existing and existing.status in _APPROVED_STATUSES:
            return DuplicateCheckResult(
                kind="exact_business",
                existing_submission_id=existing.id,
                message="An approved invoice with this supplier and invoice number already exists.",
            )
        return DuplicateCheckResult(
            kind="exact_file",
            existing_submission_id=file_dup,
            message="This document file was already uploaded.",
        )
    exact = find_business_duplicate(
        db, tenant_id, supplier_key, invoice_number_norm, exclude_id=exclude_id
    )
    if exact:
        if exact.status in _APPROVED_STATUSES:
            return DuplicateCheckResult(
                kind="exact_business",
                existing_submission_id=exact.id,
                message="An approved invoice with this supplier and invoice number already exists.",
            )
        return DuplicateCheckResult(
            kind="exact_business",
            existing_submission_id=exact.id,
            message="An active invoice with this supplier and invoice number already exists.",
        )
    potential = find_potential_duplicate(
        db, tenant_id, supplier_key, grand_total, invoice_date, exclude_id=exclude_id
    )
    if potential:
        return DuplicateCheckResult(
            kind="potential",
            existing_submission_id=potential.id,
            message="A similar invoice exists for review (same supplier, date, and amount).",
        )
    return DuplicateCheckResult(kind="none")


def assert_not_blocking_duplicate(result: DuplicateCheckResult) -> None:
    from fastapi import HTTPException

    if result.kind in ("exact_business",) and result.existing_submission_id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "duplicate_invoice",
                "message": result.message,
                "existing_submission_id": result.existing_submission_id,
            },
        )