"""Upgrade Phase 1 migration on a disposable PostgreSQL database (never touches bharathi_erp).

Usage (from backend/):
  python scripts/test_phase1_migration_disposable.py
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    env = dotenv_values(ROOT / ".env")
    base_url = (env.get("DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()
    if not base_url or "postgresql" not in base_url:
        print("BLOCKED: DATABASE_URL must be PostgreSQL")
        return 2
    if base_url.rsplit("/", 1)[-1] == "bharathi_erp":
        pass
    admin_url = base_url.rsplit("/", 1)[0] + "/postgres"
    test_db = f"bharathi_migration_test_{uuid.uuid4().hex[:8]}"
    test_url = f"{base_url.rsplit('/', 1)[0]}/{test_db}"

    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{test_db}"'))
    try:
        os.environ["DATABASE_URL"] = test_url
        os.environ.pop("ALLOW_SQLITE_RUNTIME", None)
        from alembic import command
        from alembic.config import Config
        from app.core.config import get_settings

        get_settings.cache_clear()
        cfg = Config(str(ROOT / "alembic.ini"))
        command.upgrade(cfg, "head")
        eng = create_engine(test_url)
        with eng.connect() as conn:
            cols = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='bharathi_bill_submissions' AND column_name='supplier_name'"
                )
            ).fetchall()
            assert cols, "supplier_name column missing"
            idx = conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE indexname='uq_bharathi_active_invoice_business_key'")
            ).fetchall()
            assert idx, "partial unique index missing"
        command.downgrade(cfg, "b0a1r2a3t4h5i")
        with eng.connect() as conn:
            assert not conn.execute(
                text(
                    "SELECT to_regclass('public.bharathi_purchase_invoice_lines')"
                )
            ).scalar(), "lines table should be dropped on downgrade"
        print(f"PASS: migration tested on disposable DB {test_db}")
        return 0
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{test_db}" WITH (FORCE)'))


if __name__ == "__main__":
    raise SystemExit(main())