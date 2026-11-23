from decimal import Decimal

from app.core.database import SessionLocal
from app.models.bharathi import BharathiBillSubmission
from app.services.bharathi.duplicate_detection import norm_invoice_number, supplier_identity_key
from app.services.bharathi.supplier_summary_service import approved_grand_total, list_supplier_summaries


def test_supplier_summary_aggregates():
    db = SessionLocal()
    try:
        key = supplier_identity_key(gstin="29TSTSUM0001Z5", supplier_name="Summary Vendor", vendor_hint=None)
        inv = norm_invoice_number("SUM-1")
        db.add(
            BharathiBillSubmission(
                tenant_id=1,
                submitted_by_user_id=1,
                status="APPROVED",
                supplier_identity_key=key,
                supplier_name="Summary Vendor",
                invoice_number="SUM-1",
                invoice_number_norm=inv,
                grand_total=Decimal("100.00"),
            )
        )
        db.add(
            BharathiBillSubmission(
                tenant_id=1,
                submitted_by_user_id=1,
                status="PENDING_VERIFICATION",
                supplier_identity_key=key,
                supplier_name="Summary Vendor",
                invoice_number="SUM-2",
                invoice_number_norm=norm_invoice_number("SUM-2"),
                grand_total=Decimal("50.00"),
            )
        )
        db.commit()
        items = list_supplier_summaries(db, 1, limit=50)
        match = next((i for i in items if i["supplier_identity_key"] == key), None)
        assert match is not None
        assert match["invoice_count"] >= 2
        assert match["pending_count"] >= 1
        assert Decimal(match["approved_total"]) >= Decimal("100")
        assert approved_grand_total(db, 1) >= Decimal("100")
    finally:
        db.close()