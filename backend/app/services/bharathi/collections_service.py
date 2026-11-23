"""Accounts receivable collections — aging buckets (synthetic + follow-up rows)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bharathi import BharathiCollectionFollowUp


def aging_bucket(days_overdue: int) -> str:
    if days_overdue <= 30:
        return "0-30"
    if days_overdue <= 60:
        return "31-60"
    if days_overdue <= 90:
        return "61-90"
    return "90+"


def build_aging_snapshot(rows: list[BharathiCollectionFollowUp], today: date | None = None) -> list[dict]:
    today = today or date.today()
    out = []
    for row in rows:
        due = row.due_date
        overdue_days = (today - due).days if due and due < today else 0
        remaining = float(row.outstanding_amount or Decimal("0"))
        out.append(
            {
                "id": row.id,
                "customer_id": row.customer_id,
                "invoice_ref": row.invoice_ref,
                "outstanding_amount": remaining,
                "due_date": due.isoformat() if due else None,
                "overdue_days": overdue_days,
                "aging_bucket": aging_bucket(overdue_days) if overdue_days > 0 else "0-30",
                "collection_status": row.collection_status,
                "next_follow_up_date": row.next_follow_up_date.isoformat() if row.next_follow_up_date else None,
            }
        )
    return out


def list_followups(db: Session, tenant_id: int) -> list[dict]:
    rows = list(
        db.scalars(
            select(BharathiCollectionFollowUp)
            .where(BharathiCollectionFollowUp.tenant_id == tenant_id)
            .order_by(BharathiCollectionFollowUp.id.desc())
        ).all()
    )
    return build_aging_snapshot(rows)