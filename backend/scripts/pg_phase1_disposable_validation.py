"""Full Phase 1 migration validation on a disposable PostgreSQL DB (not bharathi_erp).

Set MIGRATION_TEST_DATABASE_URL to the disposable database connection string.

Does NOT create or drop databases.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def main() -> int:
    test_url = (os.environ.get("MIGRATION_TEST_DATABASE_URL") or "").strip()
    if not test_url:
        print("BLOCKED: MIGRATION_TEST_DATABASE_URL not set")
        return 2
    db_part = test_url.split("?")[0].rstrip("/").split("/")[-1]
    if db_part == "bharathi_erp":
        return _fail("MIGRATION_TEST_DATABASE_URL must not point at bharathi_erp")

    os.environ["DATABASE_URL"] = test_url
    os.environ.pop("ALLOW_SQLITE_RUNTIME", None)

    from alembic import command
    from alembic.config import Config
    from app.core.config import get_settings

    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    eng = create_engine(test_url)

    with eng.connect() as conn:
        db = conn.execute(text("SELECT current_database()")).scalar()
        _ok(f"database identity verified: {db}")
        if db == "bharathi_erp":
            return _fail("refusing bharathi_erp")

    command.upgrade(cfg, "head")
    _ok("upgrade head")

    with eng.connect() as conn:
        for tbl in ("bharathi_purchase_invoice_lines", "bharathi_bill_ocr_jobs"):
            if not conn.execute(text("SELECT to_regclass(:n)"), {"n": f"public.{tbl}"}).scalar():
                return _fail(f"missing {tbl}")
        if not conn.execute(
            text(
                "SELECT 1 FROM pg_indexes WHERE indexname='uq_bharathi_active_invoice_business_key'"
            )
        ).fetchone():
            return _fail("partial unique index missing")
        fks = conn.execute(
            text(
                """
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'bharathi_purchase_invoice_lines'::regclass AND contype='f'
                """
            )
        ).fetchall()
        if len(fks) < 2:
            return _fail("expected FK constraints on invoice lines")
    _ok("tables, index, FKs present")

    # Resolve tenant_id from existing row or tenants table
    with eng.connect() as conn:
        tid = conn.execute(text("SELECT id FROM tenants ORDER BY id LIMIT 1")).scalar()
        if not tid:
            return _fail("no tenant in disposable DB after upgrade (register flow or seed required)")

    with eng.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO bharathi_bill_submissions
                (tenant_id, submitted_by_user_id, status, supplier_identity_key, invoice_number_norm, created_at, updated_at)
                SELECT :t, 1, 'VERIFIED', 'name:testvendor', 'INV-DUP-1', NOW(), NOW()
                WHERE NOT EXISTS (
                  SELECT 1 FROM bharathi_bill_submissions
                  WHERE tenant_id=:t AND supplier_identity_key='name:testvendor' AND invoice_number_norm='INV-DUP-1'
                    AND status='VERIFIED'
                )
                """
            ),
            {"t": tid},
        )

    dup_violation = False
    try:
        with eng.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO bharathi_bill_submissions
                    (tenant_id, submitted_by_user_id, status, supplier_identity_key, invoice_number_norm, created_at, updated_at)
                    VALUES (:t, 1, 'VERIFIED', 'name:testvendor', 'INV-DUP-1', NOW(), NOW())
                    """
                ),
                {"t": tid},
            )
    except Exception as exc:
        dup_violation = "UniqueViolation" in type(exc).__name__ or "unique" in str(exc).lower()
    if not dup_violation:
        return _fail("partial unique index did not block duplicate VERIFIED row")
    _ok("duplicate partial unique index enforced")

    command.downgrade(cfg, "b0a1r2a3t4h5i")
    _ok("downgrade b0a1r2a3t4h5i")

    with eng.connect() as conn:
        if conn.execute(text("SELECT to_regclass('public.bharathi_purchase_invoice_lines')")).scalar():
            return _fail("lines table remained after downgrade")
        retained = conn.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name='bharathi_bill_submissions' AND column_name='supplier_name')"
            )
        ).scalar()
    _ok(f"downgrade removed child tables; supplier_name column retained={bool(retained)}")

    command.upgrade(cfg, "head")
    _ok("re-upgrade head")

    from app.models.bharathi import BharathiBillSubmission
    from app.models.user import User
    from app.services.bharathi.invoice_workflow import approve_submission

    SessionLocal = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.tenant_id == tid).first()
        if not user:
            return _fail("no user for concurrency test on disposable DB")

        sub_a = BharathiBillSubmission(
            tenant_id=tid,
            submitted_by_user_id=user.id,
            status="VERIFIED",
            supplier_identity_key="name:conca",
            invoice_number_norm="CONC-A",
            duplicate_status="none",
        )
        sub_b = BharathiBillSubmission(
            tenant_id=tid,
            submitted_by_user_id=user.id,
            status="VERIFIED",
            supplier_identity_key="name:concb",
            invoice_number_norm="CONC-B",
            duplicate_status="none",
        )
        db.add(sub_a)
        db.add(sub_b)
        db.commit()
        db.refresh(sub_a)
        db.refresh(sub_b)

        results: list = []

        def approve_one(sid: int):
            sdb = SessionLocal()
            try:
                approve_submission(sdb, sdb.get(User, user.id), sid, "pg-concurrent")
                results.append("ok")
            except Exception as exc:
                results.append(type(exc).__name__)
            finally:
                sdb.close()

        t1 = threading.Thread(target=approve_one, args=(sub_a.id,))
        t2 = threading.Thread(target=approve_one, args=(sub_b.id,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        if results.count("ok") != 2:
            return _fail(f"parallel approve on distinct keys: {results}")
        _ok("concurrent approve on two distinct VERIFIED invoices")

        race_errors: list = []

        def approve_same():
            sdb = SessionLocal()
            try:
                approve_submission(sdb, sdb.get(User, user.id), sub_a.id, "race")
            except Exception as exc:
                race_errors.append(exc)
            finally:
                sdb.close()

        approve_same()
        approve_same()
        if len(race_errors) < 1:
            return _fail("second approve on already APPROVED submission should fail")
        _ok("duplicate approve on same submission rejected")

        # Tenant isolation: other tenant row must not approve with wrong tenant user
        other_tid = db.execute(text("SELECT id FROM tenants WHERE id <> :t ORDER BY id LIMIT 1"), {"t": tid}).scalar()
        if other_tid:
            foreign = BharathiBillSubmission(
                tenant_id=other_tid,
                submitted_by_user_id=user.id,
                status="VERIFIED",
                supplier_identity_key="name:iso",
                invoice_number_norm="ISO-1",
            )
            db.add(foreign)
            db.commit()
            db.refresh(foreign)
            try:
                approve_submission(db, user, foreign.id, "bad")
                return _fail("cross-tenant approve should not succeed")
            except Exception:
                _ok("tenant isolation on approve (404/403)")
    finally:
        db.close()

    print("PASS: disposable PostgreSQL migration validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())