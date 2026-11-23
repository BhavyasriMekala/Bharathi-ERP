"""Phase 1 Bharathi invoice: duplicates, OCR mock, approval."""

from decimal import Decimal

from app.core.database import SessionLocal
from app.models.bharathi import BharathiBillSubmission
from app.services.bharathi.duplicate_detection import (
    assess_duplicate,
    norm_invoice_number,
    supplier_identity_key,
)
from app.services.bharathi.invoice_validation import validate_extraction
from app.services.bharathi.invoice_extraction_schema import InvoiceExtraction
from app.services.bharathi.tally_readonly_connector import (
    MockTallyReadOnlyConnector,
    parse_tally_ledger_xml,
)


def test_supplier_key_prefers_gstin():
    assert supplier_identity_key(gstin="29AAAAA0000A1Z5", supplier_name="A", vendor_hint=None) == "gstin:29AAAAA0000A1Z5"


def test_norm_invoice_number():
    assert norm_invoice_number(" inv-12 ") == "INV-12"


def test_validation_missing_required():
    ext = InvoiceExtraction(invoice_number=None, supplier_name=None)
    codes = {w["code"] for w in validate_extraction(ext)}
    assert "missing_supplier" in codes
    assert "missing_invoice_number" in codes


def test_duplicate_different_supplier_same_number_not_exact():
    db = SessionLocal()
    try:
        k1 = supplier_identity_key(gstin=None, supplier_name="Vendor A", vendor_hint=None)
        k2 = supplier_identity_key(gstin=None, supplier_name="Vendor B", vendor_hint=None)
        assert k1 != k2
        a = BharathiBillSubmission(
            tenant_id=1,
            submitted_by_user_id=1,
            status="APPROVED",
            supplier_identity_key=k1,
            invoice_number_norm="X1",
        )
        b = BharathiBillSubmission(
            tenant_id=1,
            submitted_by_user_id=1,
            status="APPROVED",
            supplier_identity_key=k2,
            invoice_number_norm="X1",
        )
        db.add(a)
        db.add(b)
        db.commit()
        res = assess_duplicate(
            db,
            1,
            file_sha=None,
            supplier_key=k2,
            invoice_number_norm="X1",
            grand_total=Decimal("100"),
            invoice_date=None,
            exclude_id=b.id,
        )
        assert res.kind == "none"
        res_a = assess_duplicate(
            db,
            1,
            file_sha=None,
            supplier_key=k1,
            invoice_number_norm="X1",
            grand_total=Decimal("100"),
            invoice_date=None,
            exclude_id=None,
        )
        assert res_a.kind == "exact_business"
        assert res_a.existing_submission_id == a.id
    finally:
        db.close()


def test_tally_readonly_fixture_connector():
    c = MockTallyReadOnlyConnector()
    assert c.health()["ok"] is True
    assert c.company_identity().name
    assert c.list_supplier_ledgers()[0].closing_balance == Decimal("1180.00")


def test_parse_tally_ledger_xml_fixture():
    xml = """<ENVELOPE><BODY><LEDGER><NAME>Acme</NAME><CLOSINGBALANCE>1500.50</CLOSINGBALANCE></LEDGER></BODY></ENVELOPE>"""
    rows = parse_tally_ledger_xml(xml)
    assert rows[0].name == "Acme"
    assert rows[0].closing_balance == Decimal("1500.50")