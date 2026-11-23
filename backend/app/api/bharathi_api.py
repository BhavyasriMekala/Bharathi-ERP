"""Bharathi Enterprises APIs — bills, collections, Tally mock, dashboards."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user
from app.api.deps import get_db
from app.core.permissions import get_role_names, require_permission, tenant_scope, user_is_admin
from app.models.user import User
from app.schemas.bharathi import (
    BillSubmissionCreate,
    BillVerifyRequest,
    CollectionFollowUpIn,
    TallySyncRequest,
)
from app.models.bharathi import BharathiCollectionFollowUp
from app.services.bharathi.bill_service import (
    _get_submission,
    create_submission,
    list_submissions,
    submission_to_dict,
    submit_for_processing,
    verify_submission,
)
from app.services.bharathi.invoice_workflow import (
    approve_submission,
    list_submissions_paginated,
    list_verification_events,
)
from app.services.file_management_service import get_download_url
from app.services.bharathi.collections_service import list_followups
from app.services.bharathi.dashboard_service import role_dashboard
from app.services.bharathi.supplier_summary_service import list_supplier_summaries
from app.services.bharathi.tally_connector import run_inbound_sync, run_outbound_sync
from app.services.bharathi.tally_readonly_connector import get_readonly_connector
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


@router.get("/suppliers/summary")
def suppliers_summary(
    user: User = Depends(require_permission(BILLS_MODULE)),
    db: Session = Depends(get_db),
):
    return {"items": list_supplier_summaries(db, user.tenant_id, limit=80)}


@router.get("/bills/{submission_id}")
def get_bill(
    submission_id: int,
    user: User = Depends(require_permission(BILLS_MODULE)),
    db: Session = Depends(get_db),
):
    allow_all = user_is_admin(user) or "Accountant" in get_role_names(user)
    sub = _get_submission(db, user, submission_id, allow_all=allow_all)
    data = submission_to_dict(db, sub)
    for f in data.get("files") or []:
        fid = f.get("stored_file_id")
        if fid:
            try:
                url = get_download_url(db, user, int(fid))
                f["download_url"] = url.get("url") if isinstance(url, dict) else url
            except Exception:
                f["download_url"] = None
    return data


@router.get("/bills")
def list_bills(
    status: str | None = Query(None),
    supplier: str | None = Query(None),
    invoice_number: str | None = Query(None),
    duplicate_status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    paginate: bool = Query(False),
    user: User = Depends(require_permission(BILLS_MODULE)),
    db: Session = Depends(get_db),
):
    if paginate or supplier or invoice_number or duplicate_status or offset:
        subs, total = list_submissions_paginated(
            db,
            user,
            status=status,
            supplier=supplier,
            invoice_number=invoice_number,
            duplicate_status=duplicate_status,
            offset=offset,
            limit=limit,
        )
        return {
            "items": [submission_to_dict(db, s) for s in subs],
            "total": total,
            "offset": offset,
            "limit": limit,
        }
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


@router.get("/bills/{submission_id}/audit")
def bill_audit_history(
    submission_id: int,
    user: User = Depends(require_permission(BILLS_MODULE)),
    db: Session = Depends(get_db),
):
    allow_all = user_is_admin(user) or "Accountant" in get_role_names(user)
    sub = _get_submission(db, user, submission_id, allow_all=allow_all)
    return {"events": list_verification_events(db, sub.tenant_id, sub.id)}


@router.post("/bills/{submission_id}/approve")
def approve_bill(
    submission_id: int,
    payload: BillVerifyRequest,
    user: User = Depends(require_permission(BILLS_MODULE)),
    db: Session = Depends(get_db),
):
    sub = approve_submission(db, user, submission_id, payload.comment)
    return submission_to_dict(db, sub)


@router.post("/bills/{submission_id}/verify")
def verify_bill(
    submission_id: int,
    payload: BillVerifyRequest,
    user: User = Depends(require_permission(BILLS_MODULE)),
    db: Session = Depends(get_db),
):
    sub = verify_submission(
        db,
        user,
        submission_id,
        payload.action,
        payload.comment,
        payload.corrected_fields,
        [li.model_dump() for li in payload.corrected_line_items] if payload.corrected_line_items else None,
    )
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


@router.get("/tally/readonly-poc")
def tally_readonly_poc(
    user: User = Depends(require_permission(TALLY_MODULE)),
    db: Session = Depends(get_db),
):
    _ = db
    _ = user
    conn = get_readonly_connector(use_mock=True)
    health = conn.health()
    company = conn.company_identity()
    ledgers = [
        {
            "name": l.name,
            "closing_balance": str(l.closing_balance),
            "guid": l.guid,
            "gstin": l.gstin,
        }
        for l in conn.list_supplier_ledgers()
    ]
    vouchers = [
        {
            "voucher_number": v.voucher_number,
            "voucher_type": v.voucher_type,
            "party_name": v.party_name,
            "amount": str(v.amount),
            "voucher_date": v.voucher_date,
            "tally_guid": v.tally_guid,
        }
        for v in conn.list_purchase_vouchers()
    ]
    return {
        **health,
        "company": {"name": company.name, "guid": company.guid},
        "supplier_ledgers": ledgers,
        "purchase_vouchers": vouchers,
        "writes_disabled": True,
        "note": "Fixture-based read-only PoC — not a live Tally connection.",
    }


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