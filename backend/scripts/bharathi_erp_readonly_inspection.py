"""Read-only inspection of bharathi_erp for Phase 1 migration readiness (no writes)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Exact predicate from b1p1h2a3s4e5 migration partial unique index
_ACTIVE_STATUSES = (
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

PHASE1_COLUMNS = (
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


def _db_name(url: str) -> str:
    return url.rsplit("/", 1)[-1].split("?")[0]


def main() -> int:
    env = dotenv_values(ROOT / ".env")
    url = (os.environ.get("DATABASE_URL") or env.get("DATABASE_URL") or "").strip()
    if not url or "postgresql" not in url:
        print("ERROR: PostgreSQL DATABASE_URL required")
        return 2
    db_name = _db_name(url)
    print(f"database={db_name}")
    eng = create_engine(url)

    with eng.connect() as conn:
        ident = conn.execute(text("SELECT current_database(), current_user")).fetchone()
        print(f"connected_db={ident[0]} connected_user={ident[1]}")
        if ident[0] != db_name:
            print("ERROR: database identity mismatch")
            return 2
        if ident[0] == "bharathi_erp":
            print("target=production_bharathi_erp (read-only)")

        rev = None
        has_alembic = conn.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='alembic_version')"
            )
        ).scalar()
        if has_alembic:
            rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            print(f"alembic_version={rev}")

        has_sub = conn.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='bharathi_bill_submissions')"
            )
        ).scalar()
        if not has_sub:
            print("bharathi_bill_submissions=ABSENT")
            return 0

        cols = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='bharathi_bill_submissions'"
                )
            )
        }
        present = [c for c in PHASE1_COLUMNS if c in cols]
        missing = [c for c in PHASE1_COLUMNS if c not in cols]
        print(f"phase1_columns_present={len(present)}/{len(PHASE1_COLUMNS)}")
        if missing:
            print(f"phase1_columns_missing={','.join(missing)}")
        else:
            print("phase1_columns_missing=none")

        inv_count = conn.execute(text("SELECT COUNT(*) FROM bharathi_bill_submissions")).scalar()
        print(f"invoice_submission_count={inv_count}")

        statuses_in = ", ".join(f"'{s}'" for s in _ACTIVE_STATUSES)
        if "supplier_identity_key" in cols and "invoice_number_norm" in cols:
            null_keys = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM bharathi_bill_submissions
                    WHERE status IN ({statuses_in})
                      AND (supplier_identity_key IS NULL OR invoice_number_norm IS NULL)
                    """
                )
            ).scalar()
            print(f"active_rows_with_null_business_key={null_keys}")

            dup_groups = conn.execute(
                text(
                    f"""
                    SELECT tenant_id, COUNT(*) AS row_count
                    FROM bharathi_bill_submissions
                    WHERE supplier_identity_key IS NOT NULL
                      AND invoice_number_norm IS NOT NULL
                      AND status = ANY(ARRAY[{statuses_in}]::varchar[])
                    GROUP BY tenant_id, supplier_identity_key, invoice_number_norm
                    HAVING COUNT(*) > 1
                    """
                )
            ).fetchall()
            print(f"index_blocking_duplicate_groups={len(dup_groups)}")
            if dup_groups:
                for tenant_id, row_count in dup_groups[:20]:
                    print(f"  tenant_id={tenant_id} conflicting_active_rows={row_count}")
                if len(dup_groups) > 20:
                    print(f"  ... {len(dup_groups) - 20} more groups")
        else:
            print("active_rows_with_null_business_key=SKIPPED (columns not migrated)")
            print("index_blocking_duplicate_groups=SKIPPED (columns not migrated)")

        has_idx = conn.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_indexes "
                "WHERE schemaname='public' AND indexname='uq_bharathi_active_invoice_business_key')"
            )
        ).scalar()
        print(f"partial_unique_index_present={bool(has_idx)}")

        for tbl in ("bharathi_purchase_invoice_lines", "bharathi_bill_ocr_jobs"):
            exists = conn.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name=:t)"
                ),
                {"t": tbl},
            ).scalar()
            print(f"table_{tbl}={exists}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())