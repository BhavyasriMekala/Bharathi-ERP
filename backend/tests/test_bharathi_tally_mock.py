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