#!/usr/bin/env python3
"""Seed fictional Bharathi purchase invoices for client demos (idempotent).

Does not delete or overwrite unrelated ERP rows. Skips when demo markers already present.

Env:
  BHARATHI_DEMO_DATABASE=bharathi_migration_test  (recommended; keeps bharathi_erp unchanged)
  Or run check_bharathi_demo_readiness.py first.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine.url import make_url

load_dotenv(ROOT / ".env", override=True)

from app.core.config import get_settings
from app.core.local_demo_login import LOCAL_DEMO_ACCOUNT_EMAIL_BY_ROLE
from app.models.bharathi import (
    BharathiBillExtraction,
    BharathiBillSubmission,
    BharathiPurchaseInvoiceLine,
)
from app.models.user import User
from app.services.bharathi.duplicate_detection import norm_invoice_number, supplier_identity_key

MARKER = "bharathi-demo-fiction-20261123"
TENANT_ID = 1


def _engine():
    get_settings.cache_clear()
    u = make_url(get_settings().database_url)
    override = (os.getenv("BHARATHI_DEMO_DATABASE") or "").strip()
    if override:
        u = u.set(database=override)
    return create_engine(u), (u.database or "")


def _require_schema(conn) -> None:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='bharathi_bill_submissions' AND column_name='supplier_name'"
        )
    ).fetchone()
    if not row:
        raise SystemExit(
            "Schema missing Phase 1 columns. Set BHARATHI_DEMO_DATABASE=bharathi_migration_test "
            "or apply migration b1p1h2a3s4e5 (with operator approval on production)."
        )


FICTIONAL_SUPPLIERS = [
    ("Vikraya Steel Traders", "29FICT0001F1Z5", "INV-VST-2401", "APPROVED", Decimal("48250.00")),
    ("Vikraya Steel Traders", "29FICT0001F1Z5", "INV-VST-2402", "PENDING_VERIFICATION", Decimal("12180.50")),
    ("Namma Cement Supplies", "29FICT0002F1Z5", "NC-8842", "APPROVED", Decimal("93400.00")),
    ("Namma Cement Supplies", "29FICT0002F1Z5", "NC-8843", "VERIFIED", Decimal("15500.00")),
    ("Green Valley Polymers", "29FICT0003F1Z5", "GVP/24-118", "APPROVED", Decimal("23890.00")),
    ("Green Valley Polymers", "29FICT0003F1Z5", "GVP/24-119", "NEEDS_REVIEW", Decimal("8900.00")),
    ("Hubli Fasteners LLP", "29FICT0004F1Z5", "HF-2024-77", "APPROVED", Decimal("6705.00")),
    ("Hubli Fasteners LLP", "29FICT0004F1Z5", "HF-2024-78", "DUPLICATE_REVIEW", Decimal("6705.00")),
    ("Sri Lakshmi Electricals", "29FICT0005F1Z5", "SLE-5521", "APPROVED", Decimal("41220.00")),
    ("Sri Lakshmi Electricals", "29FICT0005F1Z5", "SLE-5522", "PENDING_VERIFICATION", Decimal("1980.00")),
    ("Coastal Pipes & Fittings", "29FICT0006F1Z5", "CPF-88/24", "APPROVED", Decimal("30560.00")),
    ("Coastal Pipes & Fittings", "29FICT0006F1Z5", "CPF-89/24", "REJECTED", Decimal("1200.00")),
    ("Deccan Industrial Gases", "29FICT0007F1Z5", "DIG-9012", "APPROVED", Decimal("18750.00")),
    ("Deccan Industrial Gases", "29FICT0007F1Z5", "DIG-9013", "EXTRACTED", Decimal("4200.00")),
    ("Sahyadri Packaging Co", "29FICT0008F1Z5", "SPC/1188", "APPROVED", Decimal("9900.00")),
    ("Sahyadri Packaging Co", "29FICT0008F1Z5", "SPC/1189", "APPROVED", Decimal("6250.00")),
    ("Metro Tools Karnataka", "29FICT0009F1Z5", "MTK-441", "PENDING_VERIFICATION", Decimal("14230.00")),
    ("Metro Tools Karnataka", "29FICT0009F1Z5", "MTK-442", "APPROVED", Decimal("7840.00")),
    ("Bhuvaneshwari Minerals", "29FICT0010F1Z5", "BM-2024-12", "APPROVED", Decimal("56200.00")),
    ("Bhuvaneshwari Minerals", "29FICT0010F1Z5", "BM-2024-13", "VERIFIED", Decimal("22100.00")),
    ("Rainbow Chem Distributors", "29FICT0011F1Z5", "RCD/778", "APPROVED", Decimal("11340.00")),
    ("Rainbow Chem Distributors", "29FICT0011F1Z5", "RCD/779", "NEEDS_REVIEW", Decimal("3300.00")),
    ("Unity Bearing House", "29FICT0012F1Z5", "UBH-55", "APPROVED", Decimal("16780.00")),
    ("Unity Bearing House", "29FICT0012F1Z5", "UBH-56", "APPROVED", Decimal("9450.00")),
]


def _demo_lines(total: Decimal) -> list[dict]:
    half = (total / 2).quantize(Decimal("0.01"))
    return [
        {
            "description": "Fictional demo line A",
            "hsn_sac": "7308",
            "quantity": Decimal("10"),
            "unit": "Nos",
            "unit_price": half / 10,
            "tax_rate": Decimal("18"),
            "line_total": half,
        },
        {
            "description": "Fictional demo line B",
            "hsn_sac": "3917",
            "quantity": Decimal("5"),
            "unit": "Kg",
            "unit_price": half / 5,
            "tax_rate": Decimal("18"),
            "line_total": half,
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    engine, db_name = _engine()
    with engine.connect() as conn:
        _require_schema(conn)
        if db_name == "bharathi_erp":
            rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if rev != "b1p1h2a3s4e5":
                raise SystemExit(
                    f"Refusing to seed production-shaped DB {db_name} at rev {rev}. "
                    "Use BHARATHI_DEMO_DATABASE=bharathi_migration_test"
                )

    from sqlalchemy.orm import Session

    session = Session(engine)
    try:
        existing = session.scalars(
            select(BharathiBillSubmission.id).where(
                BharathiBillSubmission.tenant_id == TENANT_ID,
                BharathiBillSubmission.idempotency_key.like(f"{MARKER}%"),
            ).limit(1)
        ).first()
        if existing and not args.dry_run:
            print(f"SEED=SKIPPED db={db_name} reason=demo_markers_present")
            return 0

        supervisor = None
        for email in LOCAL_DEMO_ACCOUNT_EMAIL_BY_ROLE.values():
            supervisor = session.scalars(select(User).where(User.email == email.lower())).first()
            if supervisor:
                break
        if not supervisor:
            supervisor = session.scalars(select(User).where(User.tenant_id == TENANT_ID).limit(1)).first()
        if not supervisor:
            raise SystemExit(
                "No tenant user for seeding — run scripts/setup_local_demo_users.py "
                "(optionally with BHARATHI_DEMO_DATABASE for isolated DB)."
            )

        created = 0
        for idx, (name, gstin, inv, status, total) in enumerate(FICTIONAL_SUPPLIERS, start=1):
            key = f"{MARKER}-{idx:03d}"
            sid_key = supplier_identity_key(gstin=gstin, supplier_name=name, vendor_hint=None)
            inv_norm = norm_invoice_number(inv)
            if session.scalars(
                select(BharathiBillSubmission.id).where(
                    BharathiBillSubmission.tenant_id == TENANT_ID,
                    BharathiBillSubmission.idempotency_key == key,
                )
            ).first():
                continue
            if args.dry_run:
                created += 1
                continue
            sub = BharathiBillSubmission(
                tenant_id=TENANT_ID,
                submitted_by_user_id=supervisor.id,
                status=status,
                vendor_hint=name,
                remarks="Fictional client demo — not real financial data",
                idempotency_key=key,
                submitted_at=datetime.now(timezone.utc),
                supplier_name=name,
                supplier_gstin=gstin,
                supplier_identity_key=sid_key,
                invoice_number=inv,
                invoice_number_norm=inv_norm,
                invoice_date=date(2024, 11, 1 + (idx % 20)),
                currency_code="INR",
                grand_total=total,
                duplicate_status="exact_business" if status == "DUPLICATE_REVIEW" else None,
                tally_sync_status="not_configured",
            )
            session.add(sub)
            session.flush()
            payload = {
                "supplier_name": name,
                "supplier_gstin": gstin,
                "invoice_number": inv,
                "invoice_date": str(sub.invoice_date),
                "currency": "INR",
                "grand_total": str(total),
                "line_items": [
                    {k: (str(v) if isinstance(v, Decimal) else v) for k, v in line.items()}
                    for line in _demo_lines(total)
                ],
            }
            session.add(
                BharathiBillExtraction(
                    tenant_id=TENANT_ID,
                    submission_id=sub.id,
                    provider="mock",
                    status="completed",
                    extracted_json=json.dumps(payload),
                    confidence_json=json.dumps({"grand_total": 0.92}),
                )
            )
            for n, line in enumerate(_demo_lines(total), start=1):
                session.add(
                    BharathiPurchaseInvoiceLine(
                        tenant_id=TENANT_ID,
                        submission_id=sub.id,
                        line_number=n,
                        description=line["description"],
                        hsn_sac=line["hsn_sac"],
                        quantity=line["quantity"],
                        unit=line["unit"],
                        unit_price=line["unit_price"],
                        tax_rate=line["tax_rate"],
                        line_total=line["line_total"],
                    )
                )
            created += 1
        if args.dry_run:
            print(f"SEED=DRY_RUN db={db_name} would_create={created}")
            return 0
        session.commit()
        print(f"SEED=OK db={db_name} created={created} suppliers=12 invoices={created}")
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())