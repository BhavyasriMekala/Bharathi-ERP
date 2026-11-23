"""Phase 1 migration validation — Scenario A (fresh) + B (pre-child tables), PG constraints."""

from __future__ import annotations

import os
import sys
import threading
import uuid
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import dotenv_values
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PHASE1_COLS = (
    "supplier_name",
    "supplier_identity_key",
    "invoice_number_norm",
)
ACTIVE_STATUSES = (
    "DRAFT",
    "SUBMITTED",
    "OCR_PROCESSING",
    "EXTRACTED",
    "NEEDS_REVIEW",
    "PENDING_VERIFICATION",
    "VERIFIED",
    "APPROVED",
    "DUPLICATE_REVIEW",
    "SYNC_PENDING",
)


def _url_for_db(base_url: str, db_name: str) -> str:
    p = urlparse(base_url.replace("+psycopg", "", 1))
    return urlunparse(p._replace(path=f"/{db_name}"))


def _section(title: str) -> None:
    print(f"\n=== {title} ===")


def _insert_tenant(conn, *, name: str, slug: str) -> int:
    """Insert tenant row matching ORM NOT NULL columns (disposable DBs only)."""
    conn.execute(
        text(
            """
            INSERT INTO tenants (
                name, slug, status, subscription, trial_status, trial_days, license_status,
                created_at, updated_at
            )
            VALUES (
                :n, :s, 'active', 'trial', true, 5, 'active',
                NOW(), NOW()
            )
            """
        ),
        {"n": name, "s": slug},
    )
    return int(conn.execute(text("SELECT id FROM tenants WHERE slug=:s"), {"s": slug}).scalar())


def _insert_user(conn, *, tenant_id: int, email: str) -> int:
    conn.execute(
        text(
            """
            INSERT INTO users (
                tenant_id, email, full_name, hashed_password,
                is_active, email_verified, failed_login_attempts,
                created_at, updated_at
            )
            VALUES (
                :t, :e, 'Mig User', 'x',
                true, true, 0,
                NOW(), NOW()
            )
            """
        ),
        {"t": tenant_id, "e": email},
    )
    return int(
        conn.execute(
            text("SELECT id FROM users WHERE tenant_id=:t AND email=:e"),
            {"t": tenant_id, "e": email},
        ).scalar()
    )


def _verify_schema(conn) -> list[str]:
    errs: list[str] = []
    insp = inspect(conn)
    if not insp.has_table("bharathi_purchase_invoice_lines"):
        errs.append("missing bharathi_purchase_invoice_lines")
    if not insp.has_table("bharathi_bill_ocr_jobs"):
        errs.append("missing bharathi_bill_ocr_jobs")
    cols = {c["name"] for c in insp.get_columns("bharathi_bill_submissions")}
    for c in (
        "supplier_name",
        "supplier_gstin",
        "supplier_identity_key",
        "invoice_number",
        "invoice_number_norm",
        "grand_total",
        "duplicate_status",
        "tally_sync_status",
    ):
        if c not in cols:
            errs.append(f"missing column {c}")
    if not conn.execute(
        text("SELECT 1 FROM pg_indexes WHERE indexname='uq_bharathi_active_invoice_business_key'")
    ).fetchone():
        errs.append("missing partial unique index")
    fks = conn.execute(
        text(
            "SELECT COUNT(*) FROM pg_constraint WHERE conrelid='bharathi_purchase_invoice_lines'::regclass AND contype='f'"
        )
    ).scalar()
    if fks < 2:
        errs.append("invoice lines FK count")
    return errs


def _duplicate_tests(eng, tenant_id: int, user_id: int) -> list[str]:
    errs: list[str] = []
    dup_inv = f"DUP-{uuid.uuid4().hex[:8].upper()}"

    # Same supplier + same invoice number — must fail on second VERIFIED
    try:
        with eng.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO bharathi_bill_submissions
                    (tenant_id, submitted_by_user_id, status, supplier_identity_key, invoice_number_norm, created_at, updated_at)
                    VALUES (:t, :u, 'VERIFIED', 'name:v1', :inv, NOW(), NOW())
                    """
                ),
                {"t": tenant_id, "u": user_id, "inv": dup_inv},
            )
        with eng.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO bharathi_bill_submissions
                    (tenant_id, submitted_by_user_id, status, supplier_identity_key, invoice_number_norm, created_at, updated_at)
                    VALUES (:t, :u, 'VERIFIED', 'name:v1', :inv, NOW(), NOW())
                    """
                ),
                {"t": tenant_id, "u": user_id, "inv": dup_inv},
            )
        errs.append("same supplier+invoice: expected unique violation")
    except Exception as exc:
        if "unique" not in str(exc).lower() and "UniqueViolation" not in type(exc).__name__:
            errs.append(f"same supplier+invoice: wrong error {type(exc).__name__}")

    shared_inv = f"SHARED-{uuid.uuid4().hex[:8].upper()}"
    # Different suppliers, same invoice number — must succeed
    try:
        with eng.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO bharathi_bill_submissions
                    (tenant_id, submitted_by_user_id, status, supplier_identity_key, invoice_number_norm, created_at, updated_at)
                    VALUES (:t, :u, 'VERIFIED', 'name:v2', :inv, NOW(), NOW())
                    """
                ),
                {"t": tenant_id, "u": user_id, "inv": shared_inv},
            )
    except Exception as exc:
        errs.append(f"diff supplier same invoice: {type(exc).__name__}")

    # Different tenant — same business key allowed
    other = tenant_id
    other_uid = user_id
    with eng.begin() as conn:
        slug = f"iso-{uuid.uuid4().hex[:8]}"
        other = _insert_tenant(conn, name=f"ISO Tenant {slug}", slug=slug)
        other_uid = _insert_user(conn, tenant_id=other, email=f"iso-{uuid.uuid4().hex[:8]}@test.local")
    try:
        with eng.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO bharathi_bill_submissions
                    (tenant_id, submitted_by_user_id, status, supplier_identity_key, invoice_number_norm, created_at, updated_at)
                    VALUES (:t, :u, 'VERIFIED', 'name:v1', :inv, NOW(), NOW())
                    """
                ),
                {"t": other, "u": other_uid, "inv": dup_inv},
            )
    except Exception as exc:
        errs.append(f"tenant isolation insert: {type(exc).__name__}")

    return errs


def _concurrency_tests(eng, tenant_id: int, user_id: int) -> list[str]:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.bharathi import BharathiBillSubmission
    from app.models.user import User
    from app.services.bharathi.invoice_workflow import approve_submission

    errs: list[str] = []
    SessionLocal = sessionmaker(bind=eng)
    db = SessionLocal()
    try:
        sub = BharathiBillSubmission(
            tenant_id=tenant_id,
            submitted_by_user_id=user_id,
            status="VERIFIED",
            supplier_identity_key=f"name:{uuid.uuid4().hex[:6]}",
            invoice_number_norm=f"APR-{uuid.uuid4().hex[:6]}",
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        sid = sub.id
        race: list = []

        def go():
            s = SessionLocal()
            try:
                u = s.scalars(
                    select(User).where(User.id == user_id).options(selectinload(User.roles))
                ).first()
                approve_submission(s, u, sid, "race")
                race.append("ok")
            except Exception as exc:
                race.append(type(exc).__name__)
            finally:
                s.close()

        t1, t2 = threading.Thread(target=go), threading.Thread(target=go)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        db.close()
        db = SessionLocal()
        final = db.get(BharathiBillSubmission, sid)
        if final.status != "APPROVED":
            errs.append("submission not APPROVED after race")
        elif race.count("ok") < 1:
            errs.append(f"concurrent approve same sub: {race}")
        elif race.count("ok") > 1:
            errs.append(f"race: both approve calls returned ok (app should serialize): {race}")
        if not db.execute(text("SELECT COUNT(*) FROM bharathi_bill_verification_events WHERE submission_id=:s"), {"s": sid}).scalar():
            pass
    finally:
        db.close()
    return errs


def _strip_phase1_header_columns(conn) -> None:
    """Remove Phase 1 header columns on disposable DBs to mimic bharathi_erp pre-migration shape."""
    cols = {
        c["name"]
        for c in inspect(conn).get_columns("bharathi_bill_submissions")
    }
    drop_cols = (
        "supplier_name",
        "supplier_gstin",
        "supplier_identity_key",
        "invoice_number",
        "invoice_number_norm",
        "invoice_date",
        "due_date",
        "currency_code",
        "grand_total",
        "duplicate_status",
        "validation_warnings_json",
        "verified_fields_json",
        "approved_by_user_id",
        "approved_at",
        "rejected_by_user_id",
        "rejected_at",
        "tally_sync_status",
    )
    for name in drop_cols:
        if name in cols:
            conn.execute(text(f"ALTER TABLE bharathi_bill_submissions DROP COLUMN IF EXISTS {name}"))


def _seed_child_tables_only(eng) -> None:
    """Replicate bharathi_erp anomaly: child tables before b1 header columns."""
    ddl_lines = """
    CREATE TABLE IF NOT EXISTS bharathi_purchase_invoice_lines (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER NOT NULL REFERENCES tenants(id),
        submission_id INTEGER NOT NULL REFERENCES bharathi_bill_submissions(id) ON DELETE CASCADE,
        line_number INTEGER NOT NULL DEFAULT 1,
        description VARCHAR(512),
        hsn_sac VARCHAR(32),
        quantity NUMERIC(18, 4),
        unit VARCHAR(32),
        unit_price NUMERIC(18, 4),
        discount_amount NUMERIC(18, 2),
        taxable_amount NUMERIC(18, 2),
        tax_rate NUMERIC(8, 4),
        tax_amount NUMERIC(18, 2),
        line_total NUMERIC(18, 2),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  """
    ddl_jobs = """
    CREATE TABLE IF NOT EXISTS bharathi_bill_ocr_jobs (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER NOT NULL REFERENCES tenants(id),
        submission_id INTEGER NOT NULL REFERENCES bharathi_bill_submissions(id) ON DELETE CASCADE,
        status VARCHAR(32) NOT NULL DEFAULT 'pending',
        provider VARCHAR(64),
        model_name VARCHAR(64),
        attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 3,
        error_message TEXT,
        started_at TIMESTAMPTZ,
        finished_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with eng.begin() as conn:
        conn.execute(text(ddl_lines))
        conn.execute(text(ddl_jobs))


def _ensure_accountant_role(conn, tenant_id: int, user_id: int) -> None:
    rid = conn.execute(
        text("SELECT id FROM roles WHERE tenant_id=:t AND name='Accountant' LIMIT 1"),
        {"t": tenant_id},
    ).scalar()
    if not rid:
        rid = conn.execute(
            text(
                """
                INSERT INTO roles (tenant_id, name, description, permissions, created_at, updated_at)
                VALUES (:t, 'Accountant', 'Migration validation', '[]'::json, NOW(), NOW())
                RETURNING id
                """
            ),
            {"t": tenant_id},
        ).scalar()
    linked = conn.execute(
        text("SELECT 1 FROM user_roles WHERE user_id=:u AND role_id=:r"),
        {"u": user_id, "r": rid},
    ).scalar()
    if not linked:
        conn.execute(
            text("INSERT INTO user_roles (user_id, role_id) VALUES (:u, :r)"),
            {"u": user_id, "r": rid},
        )


def _ensure_user_tenant(eng) -> tuple[int, int]:
    with eng.begin() as conn:
        tid = conn.execute(text("SELECT id FROM tenants ORDER BY id LIMIT 1")).scalar()
        if not tid:
            slug = f"mig-{uuid.uuid4().hex[:8]}"
            tid = _insert_tenant(conn, name="Migration Test Co", slug=slug)
        uid = conn.execute(text("SELECT id FROM users WHERE tenant_id=:t LIMIT 1"), {"t": tid}).scalar()
        if not uid:
            uid = _insert_user(conn, tenant_id=int(tid), email=f"mig-{uuid.uuid4().hex[:8]}@test.local")
        _ensure_accountant_role(conn, int(tid), int(uid))
    return int(tid), int(uid)


def run_scenario_a(base_url: str) -> str:
    from alembic import command
    from alembic.config import Config
    from app.core.config import get_settings

    db = "bharathi_migration_test_fresh"
    url = _url_for_db(base_url, db)
    os.environ["DATABASE_URL"] = url
    os.environ.pop("ALLOW_SQLITE_RUNTIME", None)
    get_settings.cache_clear()
    eng = create_engine(url)
    with eng.connect() as c:
        if c.execute(text("SELECT current_database()")).scalar() != db:
            return f"FAIL identity"
        if db == "bharathi_erp":
            return "FAIL refused erp"
    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    with eng.connect() as conn:
        errs = _verify_schema(conn)
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if rev != "b1p1h2a3s4e5":
            errs.append(f"revision {rev}")
    if errs:
        return "FAIL " + "; ".join(errs)
    tid, uid = _ensure_user_tenant(eng)
    dup = _duplicate_tests(eng, tid, uid)
    conc = _concurrency_tests(eng, tid, uid)
    if dup or conc:
        return "FAIL dup/conc " + "; ".join(dup + conc)
    # rollback
    command.downgrade(cfg, "b0a1r2a3t4h5i")
    with eng.connect() as conn:
        lost = conn.execute(text("SELECT to_regclass('public.bharathi_purchase_invoice_lines')")).scalar()
        kept = "supplier_name" in {c["name"] for c in inspect(conn).get_columns("bharathi_bill_submissions")}
        if lost:
            return "FAIL lines table not dropped"
        if not kept:
            return "FAIL header cols not retained on downgrade"
    command.upgrade(cfg, "head")
    return "PASS"


def run_scenario_b(base_url: str) -> str:
    from alembic import command
    from alembic.config import Config
    from app.core.config import get_settings

    db = "bharathi_migration_test"
    url = _url_for_db(base_url, db)
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    eng = create_engine(url)
    with eng.connect() as c:
        name = c.execute(text("SELECT current_database()")).scalar()
        if name != db:
            return "FAIL identity"
    cfg = Config(str(ROOT / "alembic.ini"))
    with eng.connect() as conn:
        has_ver = conn.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='alembic_version')"
            )
        ).scalar()
        rev = (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar() if has_ver else None
        )
    if rev == "b1p1h2a3s4e5":
        command.downgrade(cfg, "b0a1r2a3t4h5i")
    command.upgrade(cfg, "b0a1r2a3t4h5i")
    with eng.begin() as conn:
        _strip_phase1_header_columns(conn)
    # Insert marker row to verify preservation
    tid, uid = _ensure_user_tenant(eng)
    marker_id = None
    with eng.begin() as conn:
        r = conn.execute(
            text(
                """
                INSERT INTO bharathi_bill_submissions
                (tenant_id, submitted_by_user_id, status, vendor_hint, created_at, updated_at)
                VALUES (:t, :u, 'DRAFT', 'marker-preserv', NOW(), NOW())
                RETURNING id
                """
            ),
            {"t": tid, "u": uid},
        )
        marker_id = r.scalar()
    _seed_child_tables_only(eng)
    with eng.connect() as conn:
        if not inspect(conn).has_table("bharathi_purchase_invoice_lines"):
            return "FAIL child table seed"
        if "supplier_name" in {c["name"] for c in inspect(conn).get_columns("bharathi_bill_submissions")}:
            return "FAIL header cols present before b1"
    command.upgrade(cfg, "b1p1h2a3s4e5")
    with eng.connect() as conn:
        errs = _verify_schema(conn)
        preserved = conn.execute(
            text("SELECT vendor_hint FROM bharathi_bill_submissions WHERE id=:id"),
            {"id": marker_id},
        ).scalar()
        if preserved != "marker-preserv":
            errs.append("marker row not preserved")
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if rev != "b1p1h2a3s4e5":
            errs.append(f"revision {rev}")
    if errs:
        return "FAIL " + "; ".join(errs)
    dup = _duplicate_tests(eng, tid, uid)
    conc = _concurrency_tests(eng, tid, uid)
    if dup or conc:
        return "FAIL dup/conc " + "; ".join(dup + conc)
    command.downgrade(cfg, "b0a1r2a3t4h5i")
    with eng.connect() as conn:
        lines_gone = not conn.execute(text("SELECT to_regclass('public.bharathi_purchase_invoice_lines')")).scalar()
        marker = conn.execute(text("SELECT vendor_hint FROM bharathi_bill_submissions WHERE id=:id"), {"id": marker_id}).scalar()
        if not lines_gone:
            return "FAIL downgrade child tables"
        if marker != "marker-preserv":
            return "FAIL marker lost after downgrade"
    command.upgrade(cfg, "head")
    return "PASS"


def main() -> int:
    base = (dotenv_values(ROOT / ".env").get("DATABASE_URL") or "").strip()
    if not base:
        return 2
    for db in ("bharathi_migration_test", "bharathi_migration_test_fresh"):
        try:
            eng = create_engine(_url_for_db(base, db))
            with eng.connect() as c:
                c.execute(text("SELECT 1"))
            print(f"{db}=REACHABLE")
        except Exception as exc:
            print(f"{db}=UNREACHABLE {type(exc).__name__}")
            print("Run administrator CREATE DATABASE (see docs/BHARATHI_PHASE1_MIGRATION_READINESS.md)")
            return 2
    _section("Scenario A — fresh full chain")
    ra = run_scenario_a(base)
    print(ra)
    _section("Scenario B — b0a1 + pre-existing child tables")
    rb = run_scenario_b(base)
    print(rb)
    with create_engine(base).connect() as c:
        print(f"\nbharathi_erp_revision={c.execute(text('SELECT version_num FROM alembic_version')).scalar()}")
    ok = ra.startswith("PASS") and rb.startswith("PASS")
    print("\nSUITE=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())