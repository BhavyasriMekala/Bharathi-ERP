from app.core.database import SessionLocal
from app.services.bharathi.tally_connector import MockTallyConnector, run_inbound_sync, run_outbound_sync


def test_mock_tally_voucher_idempotent(client, register_admin):
    admin = register_admin()
    tenant_id = admin["user"]["tenant_id"]
    db = SessionLocal()
    try:
        run1 = run_inbound_sync(db, tenant_id, dry_run=False)
        run2 = run_inbound_sync(db, tenant_id, dry_run=False)
        assert run1.status == "complete"
        assert run2.status == "complete"
        out = run_outbound_sync(
            db,
            tenant_id,
            {"idempotency_key": "k1", "entity_type": "sales"},
            dry_run=False,
        )
        dup = run_outbound_sync(
            db,
            tenant_id,
            {"idempotency_key": "k1", "entity_type": "sales"},
            dry_run=False,
        )
        assert dup.id == out.id
    finally:
        db.close()


def test_mock_connector_fetch():
    vouchers, cursor = MockTallyConnector().fetch_vouchers(cursor=None)
    assert vouchers
    assert cursor


def test_tally_readonly_poc_api(client, register_admin, make_restricted_user):
    admin = register_admin()
    tenant_id = admin["user"]["tenant_id"]
    acct = make_restricted_user(
        tenant_id,
        ["dashboard", "bharathi_bills", "bharathi_tally"],
        role_name="Accountant",
    )
    res = client.get("/bharathi/tally/readonly-poc", headers=acct["headers"])
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["live_tally"] is False
    assert body["writes_disabled"] is True
    assert body["supplier_ledgers"]
    assert body["purchase_vouchers"]