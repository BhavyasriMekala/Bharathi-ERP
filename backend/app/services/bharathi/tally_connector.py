"""Tally integration — mock adapter + outbox (no live Tally in development)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bharathi import BharathiTallySyncItem, BharathiTallySyncRun


class MockTallyConnector:
    """Simulates office Tally responses for fixture-based tests."""

    def fetch_vouchers(self, *, cursor: str | None) -> tuple[list[dict], str]:
        vouchers = [
            {
                "tally_guid": "mock-guid-purchase-1",
                "voucher_type": "Purchase",
                "voucher_number": "PUR-0001",
                "party_name": "Fixture Vendor",
                "amount": 1180.0,
                "financial_year": "2026-27",
            }
        ]
        return vouchers, "cursor-mock-1"

    def push_voucher(self, payload: dict) -> dict:
        key = payload.get("idempotency_key") or str(uuid.uuid4())
        return {"status": "ok", "tally_voucher_key": f"mock-{key}", "duplicate": False}


def run_inbound_sync(db: Session, tenant_id: int, dry_run: bool = True) -> BharathiTallySyncRun:
    run = BharathiTallySyncRun(
        tenant_id=tenant_id,
        direction="inbound",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()
    connector = MockTallyConnector()
    vouchers, cursor = connector.fetch_vouchers(cursor=None)
    imported = 0
    for v in vouchers:
        key = f"{v['voucher_type']}:{v['tally_guid']}:{v['financial_year']}"
        existing = db.scalar(
            select(BharathiTallySyncItem).where(
                BharathiTallySyncItem.tenant_id == tenant_id,
                BharathiTallySyncItem.idempotency_key == key,
            )
        )
        if existing:
            continue
        if not dry_run:
            db.add(
                BharathiTallySyncItem(
                    tenant_id=tenant_id,
                    run_id=run.id,
                    idempotency_key=key,
                    entity_type="voucher",
                    direction="inbound",
                    status="imported",
                    payload_json=json.dumps(v),
                    tally_voucher_key=v["tally_guid"],
                )
            )
        imported += 1
    run.status = "complete"
    run.finished_at = datetime.now(timezone.utc)
    run.cursor_after = cursor
    run.stats_json = json.dumps({"imported": imported, "dry_run": dry_run})
    db.commit()
    db.refresh(run)
    return run


def run_outbound_sync(db: Session, tenant_id: int, voucher: dict, dry_run: bool = True) -> BharathiTallySyncItem:
    run = BharathiTallySyncRun(
        tenant_id=tenant_id,
        direction="outbound",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()
    key = voucher.get("idempotency_key") or str(uuid.uuid4())
    dup = db.scalar(
        select(BharathiTallySyncItem).where(
            BharathiTallySyncItem.tenant_id == tenant_id,
            BharathiTallySyncItem.idempotency_key == key,
        )
    )
    if dup:
        run.status = "complete"
        run.stats_json = json.dumps({"duplicate": True})
        db.commit()
        return dup
    item = BharathiTallySyncItem(
        tenant_id=tenant_id,
        run_id=run.id,
        idempotency_key=key,
        entity_type=voucher.get("entity_type", "voucher"),
        direction="outbound",
        status="pending" if dry_run else "exported",
        payload_json=json.dumps(voucher),
    )
    if not dry_run:
        ack = MockTallyConnector().push_voucher(voucher)
        item.tally_voucher_key = ack.get("tally_voucher_key")
        item.status = "exported"
    db.add(item)
    run.status = "complete"
    run.finished_at = datetime.now(timezone.utc)
    run.stats_json = json.dumps({"exported": 0 if dry_run else 1, "dry_run": dry_run})
    db.commit()
    db.refresh(item)
    return item