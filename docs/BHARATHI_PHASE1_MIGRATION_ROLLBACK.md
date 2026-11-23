# Phase 1 migration `b1p1h2a3s4e5` — rollback behavior

## Intentional partial downgrade

Downgrade **does not** drop Phase 1 columns from `bharathi_bill_submissions`. Those columns are nullable and remain after downgrade so operators can roll back application code without a full database restore.

## Downgrade removes

- Partial unique index `uq_bharathi_active_invoice_business_key` (PostgreSQL only)
- Table `bharathi_bill_ocr_jobs` (**data loss for OCR job history**)
- Table `bharathi_purchase_invoice_lines` (**data loss for normalized line items**)

## Downgrade retains

- All Phase 1 header columns on `bharathi_bill_submissions` (supplier fields, totals, approval timestamps, JSON fields, etc.)

## Re-upgrade safety

Re-running `alembic upgrade head` after downgrade:

- Recreates child tables (empty)
- Recreates partial unique index if predicate satisfied
- Does not re-add columns that already exist (idempotent column adds)

## Application rollback

If you downgrade Alembic **and** deploy older application code:

- Submissions and files remain; line-item tables are empty until re-migration + re-processing
- Header columns may contain data written by Phase 1 code; older code may ignore them

If you need a **full** rollback of schema and data, use a **PostgreSQL backup restore** (see `backend/docs/POSTGRES_BACKUP_RESTORE.md`), not `alembic downgrade` alone.