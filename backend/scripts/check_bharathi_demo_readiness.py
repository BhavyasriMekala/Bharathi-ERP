"""Verify database schema is ready for Bharathi purchase-invoice demo (no secrets printed)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine.url import make_url

load_dotenv(ROOT / ".env", override=True)

from app.core.config import get_settings

get_settings.cache_clear()


def _engine():
    u = make_url(get_settings().database_url)
    override = (os.getenv("BHARATHI_DEMO_DATABASE") or "").strip()
    if override:
        u = u.set(database=override)
    return create_engine(u), u.database


def main() -> int:
    engine, db_name = _engine()
    insp = inspect(engine)
    with engine.connect() as conn:
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    if not insp.has_table("bharathi_bill_submissions"):
        print(f"DEMO_READY=FAIL db={db_name} reason=missing_bharathi_bill_submissions")
        return 1
    cols = {c["name"] for c in insp.get_columns("bharathi_bill_submissions")}
    need = {"supplier_name", "invoice_number", "grand_total", "supplier_identity_key"}
    missing = sorted(need - cols)
    if missing:
        print(f"DEMO_READY=FAIL db={db_name} rev={rev} missing_columns={','.join(missing)}")
        print(
            "hint=Point BHARATHI_DEMO_DATABASE=bharathi_migration_test for isolated demo, "
            "or approve alembic b1p1h2a3s4e5 on bharathi_erp."
        )
        return 1
    for tbl in ("bharathi_purchase_invoice_lines", "bharathi_bill_extractions"):
        if not insp.has_table(tbl):
            print(f"DEMO_READY=FAIL db={db_name} reason=missing_{tbl}")
            return 1
    print(f"DEMO_READY=PASS db={db_name} rev={rev}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())