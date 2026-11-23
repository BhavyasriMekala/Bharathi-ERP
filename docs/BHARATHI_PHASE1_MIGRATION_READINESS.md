# Bharathi Phase 1 — PostgreSQL migration readiness (2026-11-23)

## Disposable migration test

**Result: BLOCKED (pending DBA)** — `bharathi_migration_test` does not exist; `bharathi_user` cannot `CREATE DATABASE`.

**Approved test databases** (create as superuser, then run suite):

- `bharathi_migration_test` — Scenario B (pre-child-table state)
- `bharathi_migration_test_fresh` — Scenario A (full chain from empty)

```powershell
cd backend
python scripts/ensure_migration_test_databases.py   # fails without superuser — use SQL below instead
python scripts/run_phase1_migration_validation_suite.py
```

Only `bharathi_erp` was visible to the application user.

### Administrator commands (run as superuser / CREATEDB role — **not** executed by agents)

```sql
-- Connect: psql -U postgres -h 127.0.0.1  (superuser — not bharathi_user)

CREATE DATABASE bharathi_migration_test
  WITH OWNER = bharathi_user ENCODING =UTF8 TEMPLATE = template0;

CREATE DATABASE bharathi_migration_test_fresh
  WITH OWNER = bharathi_user ENCODING =UTF8 TEMPLATE = template0;

GRANT ALL ON SCHEMA public TO bharathi_user;  -- per database via \c
```

Then:

```powershell
cd backend
python scripts/run_phase1_migration_validation_suite.py
```

Optional: load a schema snapshot from `bharathi_erp` at `b0a1r2a3t4h5i` (pg_dump schema-only) into the test DB before validation.

### Operator validation (after DB exists)

```powershell
cd backend
$env:MIGRATION_TEST_DATABASE_URL = "postgresql+psycopg://bharathi_user:<password>@127.0.0.1:5432/bharathi_migration_test"
python scripts/pg_phase1_disposable_validation.py
```

Script performs: upgrade head → index/FK checks → partial unique enforcement → downgrade → re-upgrade → PostgreSQL concurrency approve tests.

## `bharathi_erp` read-only inspection

| Check | Value |
|--------|--------|
| Database | `bharathi_erp` (verified) |
| Connected as | `bharathi_user` |
| Current revision | **`b0a1r2a3t4h5i`** |
| Expected after migration | **`b1p1h2a3s4e5`** |
| Repo Alembic head | `b1p1h2a3s4e5` |
| `bharathi_bill_submissions` rows | **0** |
| Phase 1 header columns | **0/17** (not migrated yet) |
| `bharathi_purchase_invoice_lines` | **present** |
| `bharathi_bill_ocr_jobs` | **present** |
| Partial unique index | **absent** (expected pre-migration) |
| Duplicate scan (index predicate) | **SKIPPED** until header columns exist; **0 rows** → no conflict risk today |

**Note:** Child Phase 1 tables exist without header columns — likely prior `create_all`/partial apply. Migration `b1p1h2a3s4e5` is idempotent (adds columns, skips existing tables, creates index).

## PostgreSQL concurrency tests

**Result: BLOCKED** (same as disposable DB). Implemented in `scripts/pg_phase1_disposable_validation.py` for execution on `bharathi_migration_test` only.

**Design note:** After migration, two **VERIFIED** rows with the **same** `(tenant_id, supplier_identity_key, invoice_number_norm)` are **not** permitted; concurrency is validated via parallel approve on **distinct** keys and double-approve on the **same** submission.

## Downgrade / re-upgrade

Documented: `docs/BHARATHI_PHASE1_MIGRATION_ROLLBACK.md`

- Downgrade is **intentionally partial** (drops child tables + index, retains header columns).
- Re-upgrade is **safe** (idempotent adds).
- Full schema rollback requires **backup restore**, not Alembic downgrade alone.

## Pending commands (production — **do not run until backup + optional disposable PASS**)

```powershell
cd C:\Users\satee\OneDrive\Desktop\Bharathi-Enterprises-ERP\backend

# 1) Backup (required)
python scripts/backup_postgres.py

# 2) Optional: re-run duplicate scan after upgrade columns exist (same predicate as migration)
python scripts/bharathi_erp_readonly_inspection.py

# 3) Apply migration (operator approval)
alembic upgrade head

# 4) Verify revision
python scripts/check_alembic_revision.py
```

## Backup and recovery

1. `python scripts/backup_postgres.py` → `backend/backups/insights_iva_<timestamp>.sql`
2. Restore: see `backend/docs/POSTGRES_BACKUP_RESTORE.md` (`restore_postgres_disposable.py` pattern)
3. If upgrade fails mid-flight: restore backup; do not hand-edit production schema
4. If downgrade used: line-item and OCR job **data in child tables is lost**; header columns remain

## Recommendation

| Gate | Status |
|------|--------|
| Production data conflicts | **CLEAR** (0 submissions) |
| Disposable PG full cycle | **NOT RUN** |
| Read-only production inspection | **PASS** |
| **Overall** | **CONDITIONAL GO** |

**GO** to run `alembic upgrade head` on `bharathi_erp` **after**:

1. Successful backup, and  
2. Strongly recommended: disposable DB validation via `pg_phase1_disposable_validation.py`, and  
3. Post-upgrade `check_alembic_revision.py` shows `db_revision=b1p1h2a3s4e5`.