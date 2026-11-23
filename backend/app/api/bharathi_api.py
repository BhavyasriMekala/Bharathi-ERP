"""Bharathi Enterprises APIs — bills, collections, Tally mock, dashboards."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user
from app.api.deps import get_db
from app.core.permissions import require_permission, tenant_scope
from app.models.user import User
from app.schemas.bharathi import (
    BillSubmissionCreate,
    BillVerifyRequest,
    CollectionFollowUpIn,
    TallySyncRequest,
)
from app.models.bharathi import BharathiCollectionFollowUp
from app.services.bharathi.bill_service import (
    create_submission,
    list_submissions,
    submission_to_dict,
    submit_for_processing,
    verify_submission,
)
from app.services.bharathi.collections_service import list_followups
from app.services.bharathi.dashboard_service import role_dashboard
from app.services.bharathi.tally_connector import run_inbound_sync, run_outbound_sync
from app.services.bharathi.company_profile import ensure_bharathi_company_profile
from app.services.bharathi.vendor_pricing_service import compare_vendor_rows
from app.core.permissions import require_admin

router = APIRouter(prefix="/bharathi", tags=["bharathi"])
BILLS_MODULE = "bharathi_bills"
TALLY_MODULE = "bharathi_tally"
COLLECTIONS_MODULE = "bharathi_collections"


@router.post("/company-profile/ensure")
def ensure_company_profile(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = ensure_bharathi_company_profile(db, user.tenant_id)
    return {"company_name": row.company_name, "country": row.country, "gstin": row.gstin}


@router.get("/dashboard")
def bharathi_dashboard(
    user: User = Depends(require_permission("dashboard")),
    db: Session = Depends(get_db),
):
    return role_dashboard(db, user)


@router.get("/bills")
def list_bills(
    status: str | None = Query(None),
    user: User = Depends(require_permission(BILLS_MODULE)),
    db: Session = Depends(get_db),
):
    subs = list_submissions(db, user, status=status)
    return [submission_to_dict(db, s) for s in subs]


@router.post("/bills")
def create_bill(
    payload: BillSubmissionCreate,
    user: User = Depends(require_permission(BILLS_MODULE)),
    db: Session = Depends(get_db),
):
    sub = create_submission(db, user, payload.model_dump())
    return submission_to_dict(db, sub)


@router.post("/bills/{submission_id}/submit")
def submit_bill(
    submission_id: int,
    user: User = Depends(require_permission(BILLS_MODULE)),
    db: Session = Depends(get_db),
):
    sub = submit_for_processing(db, user, submission_id)
    return submission_to_dict(db, sub)


@router.post("/bills/{submission_id}/verify")
def verify_bill(
    submission_id: int,
    payload: BillVerifyRequest,
    user: User = Depends(require_permission(BILLS_MODULE)),
    db: Session = Depends(get_db),
):
    sub = verify_submission(db, user, submission_id, payload.action, payload.comment, payload.corrected_fields)
    return submission_to_dict(db, sub)


@router.get("/collections/outstanding")
def collections_outstanding(
    tenant_id: int = Depends(tenant_scope(COLLECTIONS_MODULE)),
    user: User = Depends(require_permission(COLLECTIONS_MODULE)),
    db: Session = Depends(get_db),
):
    _ = user
    return {"items": list_followups(db, tenant_id)}


@router.post("/collections/follow-ups")
def create_follow_up(
    payload: CollectionFollowUpIn,
    tenant_id: int = Depends(tenant_scope(COLLECTIONS_MODULE)),
    user: User = Depends(require_permission(COLLECTIONS_MODULE)),
    db: Session = Depends(get_db),
):
    row = BharathiCollectionFollowUp(
        tenant_id=tenant_id,
        customer_id=payload.customer_id,
        invoice_ref=payload.invoice_ref,
        outstanding_amount=payload.outstanding_amount,
        due_date=payload.due_date,
        next_follow_up_date=payload.next_follow_up_date,
        collection_status=payload.collection_status,
        notes=payload.notes,
        follow_up_owner_user_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id}


@router.post("/procurement/vendor-price-compare")
def vendor_price_compare(
    rows: list[dict],
    user: User = Depends(require_permission("procurement")),
    db: Session = Depends(get_db),
):
    _ = db
    _ = user
    return {"comparisons": compare_vendor_rows(rows)}


@router.post("/tally/sync")
def tally_sync(
    payload: TallySyncRequest,
    tenant_id: int = Depends(tenant_scope(TALLY_MODULE)),
    user: User = Depends(require_permission(TALLY_MODULE)),
    db: Session = Depends(get_db),
):
    _ = user
    if payload.direction == "inbound":
        run = run_inbound_sync(db, tenant_id, dry_run=payload.dry_run)
        return {"run_id": run.id, "status": run.status, "stats": run.stats_json}
    item = run_outbound_sync(
        db,
        tenant_id,
        {"idempotency_key": "dry-run-export", "entity_type": "sales_invoice", "amount": 0},
        dry_run=payload.dry_run,
    )
    return {"item_id": item.id, "status": item.status}