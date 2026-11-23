"""Role-specific Bharathi dashboard KPIs."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import get_role_names, user_is_admin
from app.models.bharathi import BharathiBillSubmission, BharathiTallySyncRun
from app.models.user import User


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
    base = {
        "pending_bill_verification": int(pending_verification or 0),
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
    return base