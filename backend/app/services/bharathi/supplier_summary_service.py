"""Supplier-wise invoice rollups for Bharathi demo dashboards."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.bharathi import BharathiBillSubmission

_PENDING_STATUSES = frozenset(
    {
        "PENDING_VERIFICATION",
        "NEEDS_REVIEW",
        "DUPLICATE_REVIEW",
        "VERIFIED",
        "EXTRACTED",
        "SUBMITTED",
        "OCR_PROCESSING",
    }
)


def invoice_totals_by_status(db: Session, tenant_id: int) -> dict[str, int]:
    rows = db.execute(
        select(BharathiBillSubmission.status, func.count())
        .where(BharathiBillSubmission.tenant_id == tenant_id)
        .group_by(BharathiBillSubmission.status)
    ).all()
    return {str(status): int(count) for status, count in rows}


def approved_grand_total(db: Session, tenant_id: int) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(BharathiBillSubmission.grand_total), 0)).where(
            BharathiBillSubmission.tenant_id == tenant_id,
            BharathiBillSubmission.status == "APPROVED",
        )
    )
    return Decimal(str(value or 0))


def pending_approval_count(db: Session, tenant_id: int) -> int:
    value = db.scalar(
        select(func.count())
        .select_from(BharathiBillSubmission)
        .where(
            BharathiBillSubmission.tenant_id == tenant_id,
            BharathiBillSubmission.status.in_(tuple(_PENDING_STATUSES)),
        )
    )
    return int(value or 0)


def list_supplier_summaries(db: Session, tenant_id: int, *, limit: int = 80) -> list[dict]:
    pending_case = case(
        (BharathiBillSubmission.status.in_(tuple(_PENDING_STATUSES)), 1),
        else_=0,
    )
    approved_amt = case(
        (BharathiBillSubmission.status == "APPROVED", BharathiBillSubmission.grand_total),
        else_=0,
    )
    stmt = (
        select(
            BharathiBillSubmission.supplier_identity_key,
            func.max(BharathiBillSubmission.supplier_name).label("supplier_name"),
            func.max(BharathiBillSubmission.supplier_gstin).label("supplier_gstin"),
            func.count().label("invoice_count"),
            func.coalesce(func.sum(approved_amt), 0).label("approved_total"),
            func.coalesce(func.sum(pending_case), 0).label("pending_count"),
        )
        .where(
            BharathiBillSubmission.tenant_id == tenant_id,
            BharathiBillSubmission.supplier_identity_key.isnot(None),
        )
        .group_by(BharathiBillSubmission.supplier_identity_key)
        .order_by(func.max(BharathiBillSubmission.supplier_name).nulls_last())
        .limit(limit)
    )
    out: list[dict] = []
    for row in db.execute(stmt).all():
        out.append(
            {
                "supplier_identity_key": row.supplier_identity_key,
                "supplier_name": row.supplier_name,
                "supplier_gstin": row.supplier_gstin,
                "invoice_count": int(row.invoice_count or 0),
                "approved_total": str(Decimal(str(row.approved_total or 0))),
                "pending_count": int(row.pending_count or 0),
            }
        )
    return out