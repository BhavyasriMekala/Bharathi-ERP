"""Duplicate detection edge cases and approval guards."""

from decimal import Decimal

from app.core.database import SessionLocal
from app.models.bharathi import BharathiBillSubmission
from app.services.bharathi.duplicate_detection import (
    assess_duplicate,
    supplier_identity_key,
    norm_invoice_number,
)
def test_supplier_alias_normalization():
    k1 = supplier_identity_key(gstin=None, supplier_name=" ACME  Pvt Ltd ", vendor_hint=None)
    k2 = supplier_identity_key(gstin=None, supplier_name="Acme Pvt Ltd", vendor_hint="ACME Pvt Ltd")
    assert k1 == k2


def test_rejected_invoice_not_blocking_duplicate_by_default():
    db = SessionLocal()
    try:
        k = supplier_identity_key(gstin="29AAAAA0000A1Z5", supplier_name=None, vendor_hint=None)
        a = BharathiBillSubmission(
            tenant_id=1,
            submitted_by_user_id=1,
            status="REJECTED",
            supplier_identity_key=k,
            invoice_number_norm="R-100",
        )
        db.add(a)
        db.commit()
        res = assess_duplicate(
            db,
            1,
            file_sha=None,
            supplier_key=k,
            invoice_number_norm="R-100",
            grand_total=Decimal("1"),
            invoice_date=None,
        )
        assert res.kind == "none"
    finally:
        db.close()


def test_tenant_isolation():
    db = SessionLocal()
    try:
        k = supplier_identity_key(gstin=None, supplier_name="Shared Vendor", vendor_hint=None)
        a = BharathiBillSubmission(
            tenant_id=99,
            submitted_by_user_id=1,
            status="APPROVED",
            supplier_identity_key=k,
            invoice_number_norm="T1",
        )
        db.add(a)
        db.commit()
        res = assess_duplicate(
            db,
            1,
            file_sha=None,
            supplier_key=k,
            invoice_number_norm="T1",
            grand_total=Decimal("1"),
            invoice_date=None,
        )
        assert res.kind == "none"
    finally:
        db.close()


def test_approve_blocks_exact_duplicate(client, register_admin, make_restricted_user):
    from app.core.database import SessionLocal

    admin = register_admin()
    tenant_id = admin["user"]["tenant_id"]
    acct = make_restricted_user(tenant_id, ["dashboard", "bharathi_bills"], role_name="Accountant")
    admin_headers = admin["headers"]
    db = SessionLocal()
    try:
        k = supplier_identity_key(gstin=None, supplier_name="Dup Co", vendor_hint=None)
        a = BharathiBillSubmission(
            tenant_id=tenant_id,
            submitted_by_user_id=admin["user"]["id"],
            status="APPROVED",
            supplier_identity_key=k,
            invoice_number_norm="DUP-1",
            duplicate_status="exact",
        )
        b = BharathiBillSubmission(
            tenant_id=tenant_id,
            submitted_by_user_id=admin["user"]["id"],
            status="VERIFIED",
            supplier_identity_key=k,
            invoice_number_norm="DUP-1",
            duplicate_status="exact",
        )
        db.add(a)
        db.add(b)
        db.commit()
        db.refresh(b)
        bid = b.id
    finally:
        db.close()

    res = client.post(
        f"/bharathi/bills/{bid}/approve",
        json={"action": "approve"},
        headers=acct["headers"] if acct else admin_headers,
    )
    assert res.status_code == 409


def test_double_approve_rejected_after_first(client, register_admin, make_restricted_user):
    admin = register_admin()
    tenant_id = admin["user"]["tenant_id"]
    acct = make_restricted_user(tenant_id, ["dashboard", "bharathi_bills"], role_name="Accountant")
    db = SessionLocal()
    try:
        sub = BharathiBillSubmission(
            tenant_id=tenant_id,
            submitted_by_user_id=admin["user"]["id"],
            status="VERIFIED",
            supplier_identity_key="name:vendor",
            invoice_number_norm="C-1",
            duplicate_status="none",
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        sub_id = sub.id
    finally:
        db.close()

    first = client.post(f"/bharathi/bills/{sub_id}/approve", json={"action": "approve"}, headers=acct["headers"])
    assert first.status_code == 200
    second = client.post(f"/bharathi/bills/{sub_id}/approve", json={"action": "approve"}, headers=acct["headers"])
    assert second.status_code == 400