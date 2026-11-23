"""Role-specific Bharathi dashboard KPIs."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import get_role_names, user_is_admin
from app.models.bharathi import BharathiBillSubmission, BharathiTallySyncRun
from app.models.user import User
from app.services.bharathi.supplier_summary_service import (
    approved_grand_total,
    invoice_totals_by_status,
    list_supplier_summaries,
    pending_approval_count,
)


def role_dashboard(db: Session, user: User) -> dict:
    tenant_id = user.tenant_id
    roles = get_role_names(user)
    pending_verification = db.scalar(
        select(func.count())
        .select_from(BharathiBillSubmission)
        .where(
            BharathiBillSubmission.tenant_id == tenant_id,
            BharathiBillSubmission.status == "PENDING_VERIFICATION",
        )
    )
    tally_failures = db.scalar(
        select(func.count())
        .select_from(BharathiTallySyncRun)
        .where(
            BharathiTallySyncRun.tenant_id == tenant_id,
            BharathiTallySyncRun.status == "failed",
        )
    )
    status_counts = invoice_totals_by_status(db, tenant_id)
    base = {
        "pending_bill_verification": int(pending_verification or 0),
        "pending_approval_total": pending_approval_count(db, tenant_id),
        "approved_invoice_count": status_counts.get("APPROVED", 0),
        "approved_amount_inr": str(approved_grand_total(db, tenant_id)),
        "invoice_counts_by_status": status_counts,
        "supplier_count": len(list_supplier_summaries(db, tenant_id, limit=200)),
        "tally_sync_failures": int(tally_failures or 0),
        "client": "bharathi_enterprises",
    }
    if user_is_admin(user):
        base["role_view"] = "admin"
        base["kpis"] = ["sales", "purchases", "receivables", "payables", "collections"]
    elif "Accountant" in roles:
        base["role_view"] = "accountant"
        base["kpis"] = ["pending_verification", "outstanding", "tally_reconciliation"]
    elif "Supervisor" in roles:
        mine = db.scalar(
            select(func.count())
            .select_from(BharathiBillSubmission)
            .where(
                BharathiBillSubmission.tenant_id == tenant_id,
                BharathiBillSubmission.submitted_by_user_id == user.id,
            )
        )
        base["role_view"] = "supervisor"
        base["my_submissions"] = int(mine or 0)
        base["kpis"] = ["upload_bill", "my_submissions"]
    else:
        base["role_view"] = "other"
    if user_is_admin(user) or "Accountant" in roles:
        base["supplier_summaries"] = list_supplier_summaries(db, tenant_id, limit=12)
    return base