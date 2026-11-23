"""Bill upload workflow with stored file integration."""

from pathlib import Path

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.file_storage import StoredFile


def _uploaded_file(db, tenant_id: int, user_id: int) -> int:
    key = f"bharathi/test/{user_id}/bill-test.pdf"
    root = Path(get_settings().file_storage_local_path).resolve()
    path = (root / key).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4\n% mock invoice bytes for OCR tests\n")
    row = StoredFile(
        tenant_id=tenant_id,
        uploaded_by_user_id=user_id,
        original_filename="bill-test.pdf",
        storage_provider="local",
        storage_bucket="local",
        storage_key=key,
        mime_type="application/pdf",
        file_size=1024,
        checksum_sha256="abc123test",
        upload_status="UPLOADED",
        scan_status="SAFE",
        processing_status="READY",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row.id


def test_supervisor_bill_requires_stored_file(client, register_admin, make_restricted_user):
    admin = register_admin()
    tenant_id = admin["user"]["tenant_id"]
    sup = make_restricted_user(
        tenant_id,
        ["dashboard", "bharathi_bills", "documents"],
        role_name="Supervisor",
    )
    login_sup = client.post(
        "/auth/login",
        json={"email": sup["email"], "password": "Passw0rd!123", "role": "Supervisor"},
    ).json()
    user_id = login_sup["user"]["id"]
    db = SessionLocal()
    try:
        file_id = _uploaded_file(db, tenant_id, user_id)
    finally:
        db.close()

    bad = client.post(
        "/bharathi/bills",
        json={"vendor_hint": "ACME", "files": []},
        headers=sup["headers"],
    )
    assert bad.status_code == 400

    ok = client.post(
        "/bharathi/bills",
        json={
            "vendor_hint": "ACME",
            "files": [{"stored_file_id": file_id, "original_filename": "bill-test.pdf", "mime_type": "application/pdf"}],
        },
        headers=sup["headers"],
    )
    assert ok.status_code == 200
    sub_id = ok.json()["id"]

    submitted = client.post(f"/bharathi/bills/{sub_id}/submit", headers=sup["headers"])
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "PENDING_VERIFICATION"

    acct = make_restricted_user(
        tenant_id,
        ["bharathi_bills", "accounts"],
        role_name="Accountant",
    )
    verified = client.post(
        f"/bharathi/bills/{sub_id}/verify",
        json={"action": "verify", "comment": "ok"},
        headers=acct["headers"],
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "VERIFIED"

    sup_denied = client.post(
        f"/bharathi/bills/{sub_id}/verify",
        json={"action": "verify"},
        headers=sup["headers"],
    )
    assert sup_denied.status_code == 403