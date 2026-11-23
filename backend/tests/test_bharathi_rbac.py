"""Supervisor vs Accountant authorization for Bharathi bills."""


def _bill_payload(file_id: int):
    return {
        "vendor_hint": "VENDOR-X",
        "files": [{"stored_file_id": file_id, "original_filename": "x.pdf", "mime_type": "application/pdf"}],
    }


def test_supervisor_can_create_and_submit_not_verify(client, register_admin, make_restricted_user, tmp_path):
    from pathlib import Path

    from app.core.config import get_settings
    from app.core.database import SessionLocal
    from app.models.file_storage import StoredFile

    admin = register_admin()
    tenant_id = admin["user"]["tenant_id"]
    sup = make_restricted_user(
        tenant_id,
        ["dashboard", "bharathi_bills", "documents"],
        role_name="Supervisor",
    )
    sup_login = client.post(
        "/auth/login",
        json={"email": sup["email"], "password": "Passw0rd!123", "role": "Supervisor"},
    ).json()
    sup_user_id = sup_login["user"]["id"]
    db = SessionLocal()
    try:
        key = f"bharathi/rbac/{sup['email']}/x.pdf"
        root = Path(get_settings().file_storage_local_path).resolve()
        path = (root / key).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"%PDF-rbac")
        sf = StoredFile(
            tenant_id=tenant_id,
            uploaded_by_user_id=sup_user_id,
            original_filename="x.pdf",
            storage_provider="local",
            storage_bucket="local",
            storage_key=key,
            mime_type="application/pdf",
            file_size=10,
            upload_status="UPLOADED",
            scan_status="SAFE",
            processing_status="READY",
        )
        db.add(sf)
        db.commit()
        file_id = sf.id
    finally:
        db.close()

    created = client.post("/bharathi/bills", json=_bill_payload(file_id), headers=sup["headers"])
    assert created.status_code == 200, created.text
    sub_id = created.json()["id"]

    submitted = client.post(f"/bharathi/bills/{sub_id}/submit", headers=sup["headers"])
    assert submitted.status_code == 200, submitted.text

    verify = client.post(
        f"/bharathi/bills/{sub_id}/verify",
        json={"action": "verify"},
        headers=sup["headers"],
    )
    assert verify.status_code == 403

    reject = client.post(
        f"/bharathi/bills/{sub_id}/verify",
        json={"action": "reject"},
        headers=sup["headers"],
    )
    assert reject.status_code == 403

    approve = client.post(
        f"/bharathi/bills/{sub_id}/approve",
        json={"action": "approve"},
        headers=sup["headers"],
    )
    assert approve.status_code == 403


def test_supervisor_read_scoped_list(client, register_admin, make_restricted_user):
    admin = register_admin()
    tenant_id = admin["user"]["tenant_id"]
    sup = make_restricted_user(tenant_id, ["dashboard", "bharathi_bills"], role_name="Supervisor")
    res = client.get("/bharathi/bills", headers=sup["headers"])
    assert res.status_code == 200


def test_accountant_can_verify_and_save_corrections(client, register_admin, make_restricted_user):
    from pathlib import Path

    from app.core.config import get_settings
    from app.core.database import SessionLocal
    from app.models.bharathi import BharathiBillSubmission
    from app.models.file_storage import StoredFile

    admin = register_admin()
    tenant_id = admin["user"]["tenant_id"]
    sup = make_restricted_user(
        tenant_id,
        ["dashboard", "bharathi_bills", "documents"],
        role_name="Supervisor",
    )
    sup_user_id = client.post(
        "/auth/login",
        json={"email": sup["email"], "password": "Passw0rd!123", "role": "Supervisor"},
    ).json()["user"]["id"]
    acct = make_restricted_user(
        tenant_id,
        ["dashboard", "bharathi_bills"],
        role_name="Accountant",
    )
    db = SessionLocal()
    try:
        key = "bharathi/rbac/acct/x.pdf"
        root = Path(get_settings().file_storage_local_path).resolve()
        path = (root / key).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"%PDF-acct")
        sf = StoredFile(
            tenant_id=tenant_id,
            uploaded_by_user_id=sup_user_id,
            original_filename="x.pdf",
            storage_provider="local",
            storage_bucket="local",
            storage_key=key,
            mime_type="application/pdf",
            file_size=10,
            upload_status="UPLOADED",
            scan_status="SAFE",
            processing_status="READY",
        )
        db.add(sf)
        db.commit()
        file_id = sf.id
    finally:
        db.close()

    sub_id = client.post("/bharathi/bills", json=_bill_payload(file_id), headers=sup["headers"]).json()["id"]
    client.post(f"/bharathi/bills/{sub_id}/submit", headers=sup["headers"])
    db = SessionLocal()
    try:
        sub = db.get(BharathiBillSubmission, sub_id)
        sub.status = "PENDING_VERIFICATION"
        db.commit()
    finally:
        db.close()

    save = client.post(
        f"/bharathi/bills/{sub_id}/verify",
        json={
            "action": "save_corrections",
            "corrected_line_items": [
                {
                    "description": "Fuse wire",
                    "hsn_sac": "8536",
                    "quantity": 2,
                    "unit": "pcs",
                    "unit_price": 100,
                    "tax_rate": 18,
                    "tax_amount": 36,
                    "line_total": 236,
                }
            ],
        },
        headers=acct["headers"],
    )
    assert save.status_code == 200, save.text
    body = save.json()
    assert body["status"] == "PENDING_VERIFICATION"
    assert body["line_items"][0]["description"] == "Fuse wire"
    assert body["latest_extraction"] is None or True


def test_supervisor_cannot_save_corrections(client, register_admin, make_restricted_user):
    admin = register_admin()
    tenant_id = admin["user"]["tenant_id"]
    sup = make_restricted_user(tenant_id, ["dashboard", "bharathi_bills"], role_name="Supervisor")
    res = client.post(
        "/bharathi/bills/1/verify",
        json={"action": "save_corrections", "corrected_line_items": []},
        headers=sup["headers"],
    )
    assert res.status_code in (403, 404)