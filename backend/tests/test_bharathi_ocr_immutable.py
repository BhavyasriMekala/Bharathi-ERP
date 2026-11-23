"""OCR extraction rows must remain immutable when accountants save corrections."""

import json

from app.core.database import SessionLocal
from app.models.bharathi import BharathiBillExtraction, BharathiBillSubmission


def test_corrections_do_not_overwrite_extracted_json(client, register_admin, make_restricted_user):
    admin = register_admin()
    tenant_id = admin["user"]["tenant_id"]
    acct = make_restricted_user(tenant_id, ["dashboard", "bharathi_bills"], role_name="Accountant")
    db = SessionLocal()
    try:
        sub = BharathiBillSubmission(
            tenant_id=tenant_id,
            submitted_by_user_id=admin["user"]["id"],
            status="PENDING_VERIFICATION",
        )
        db.add(sub)
        db.flush()
        original = {"invoice_number": "OCR-1", "supplier_name": "Before", "line_items": [{"description": "Raw"}]}
        ext = BharathiBillExtraction(
            tenant_id=tenant_id,
            submission_id=sub.id,
            provider="mock",
            status="ok",
            extracted_json=json.dumps(original),
        )
        db.add(ext)
        db.commit()
        sub_id = sub.id
        ext_id = ext.id
    finally:
        db.close()

    res = client.post(
        f"/bharathi/bills/{sub_id}/verify",
        json={
            "action": "save_corrections",
            "corrected_fields": {"supplier_name": "After"},
            "corrected_line_items": [{"description": "Corrected", "quantity": 1, "unit_price": 10, "line_total": 10}],
        },
        headers=acct["headers"],
    )
    assert res.status_code == 200, res.text

    db = SessionLocal()
    try:
        ext = db.get(BharathiBillExtraction, ext_id)
        preserved = json.loads(ext.extracted_json)
        assert preserved["supplier_name"] == "Before"
        assert preserved["line_items"][0]["description"] == "Raw"
        sub = db.get(BharathiBillSubmission, sub_id)
        assert json.loads(sub.verified_fields_json)["header"]["supplier_name"] == "After"
    finally:
        db.close()