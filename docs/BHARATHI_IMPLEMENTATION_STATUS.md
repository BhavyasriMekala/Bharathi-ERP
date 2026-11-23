# Bharathi Implementation Status

Updated: 2026-11-23 — **Client demo first** (see `docs/BHARATHI_CLIENT_DEMO.md`)

## Phase 1 purchase invoices

| # | Feature | Status |
|---|---------|--------|
| 1 | Mobile-first Scan Invoice UI | **implemented/tested** (UI + workflow test) |
| 2 | Secure file upload (`stored_file_id`) | **implemented/tested** |
| 3 | Real OCR integration (bytes in) | **implemented/not live-verified** (OpenAI path coded; tests use `mock`) |
| 4 | Structured extraction schema | **implemented/tested** |
| 5 | Header + line-item storage | **implemented/tested** (SQLite pytest; PG needs migration) |
| 6 | Review + manual correction UI | **partial** (header fields + JSON preview; no full line grid) |
| 7 | Supplier-scoped duplicate detection | **implemented/tested** |
| 8 | DB-backed duplicate block on approve | **implemented/tested** |
| 9 | Verification workflow | **implemented/tested** |
| 10 | APPROVED / REJECTED transitions | **implemented/tested** |
| 11 | Admin/Accountant approve auth | **implemented/tested** (`assert_can_approve`) |
| 12 | Supervisor upload-only for approve | **implemented/tested** (403 on verify where restricted) |
| 13 | Searchable purchase register | **implemented/tested** (API + `/bharathi/register`) |
| 14 | Invoice audit history | **implemented/tested** (API + verification queue) |
| 15 | Bharathi route permissions | **implemented/tested** |
| 16 | Bharathi sidebar filtering | **implemented/tested** (`bharathiClient.test.js`) |
| 17 | Backend tests + frontend build | **implemented/tested** (14 backend; full vitest 1 legacy fail; build OK) |

## Tally read-only PoC

| Item | Status |
|------|--------|
| Read-only connector interface | **implemented/tested** |
| Fixture ledger + purchase voucher parsing | **implemented/tested** |
| Company identity mapping | **implemented/tested** |
| Safe error handling | **implemented/tested** |
| Decimal-safe amounts | **implemented/tested** |
| Duplicate import identity (design) | **implemented** (mock outbound sync keys) |
| Windows connector architecture doc | **implemented** (`docs/BHARATHI_TALLY_READONLY_POC.md`) |
| Automated read-only tests | **implemented/tested** |
| `GET /bharathi/tally/readonly-poc` | **implemented/tested** |
| Live Tally connection | **not implemented** (by design) |

## Store Manager

- Role preserved; demo login preserved; inventory routes unchanged.
- Hidden from Bharathi purchase nav when `BHARATHI_CLIENT_MODE`; no invoice approval.

## Migrations

| File | Applied to `bharathi_erp` |
|------|---------------------------|
| `backend/alembic/versions/b1p1h2a3s4e5_phase1_bharathi_invoice.py` | **No** — requires your approval |

## OCR provider

- Code: `ocr_providers.py` (`mock`, `openai`, `auto`).
- Local pytest: `BHARATHI_OCR_PROVIDER=mock`.
- Live OpenAI: **not live-verified** in this environment.

## Tests run (this pass)

```
pytest tests/test_bharathi_phase1.py tests/test_bharathi_bill_workflow.py \
  tests/test_bharathi_tally_mock.py tests/test_bharathi_bills.py  → 14 passed
vitest src/config/bharathiClient.test.js → passed
npm run build → success (~2m)
```

Full `npm test`: 1 pre-existing failure in `sidebarNav.jobCards.test.js` (nav order vs Settings).

## Demo database blocker (`bharathi_erp`)

- Production DB is at **`b0a1r2a3t4h5i`** without Phase 1 header columns → bill APIs **fail** until **`b1p1h2a3s4e5`**.
- **`bharathi_migration_test`** is at **`b1p1h2a3s4e5`** with demo seed (24 fictional invoices, 12 suppliers).

## Requires your approval

1. `alembic upgrade head` on `bharathi_erp` (only when moving demo off isolated DB).
2. Optional: set `BHARATHI_OCR_PROVIDER=openai` + `OPENAI_API_KEY` for live OCR smoke test.
3. Production deploy / push (explicitly out of scope for agents).

## Local verification steps

1. Approve and run migration on `bharathi_erp` (or disposable Postgres with `USE_POSTGRES_TESTS=1`).
2. `python scripts/setup_local_demo_users.py` if demo users need refresh.
3. Backend: `uvicorn app.main:app --reload` from `backend/`.
4. Frontend: `npm run dev` from `frontend/` with Bharathi client mode env flags if used.
5. Supervisor: `/bharathi/bills` — scan/upload → submit for OCR.
6. Accountant: `/bharathi/verification` — verify/approve; check audit list.
7. Register: `/bharathi/register` — search filters.
8. Tally: `/bharathi/tally` — read-only PoC panel (fixture data).

## Docs added/updated

- `BHARATHI_PHASE1_IMPLEMENTATION.md`
- `BHARATHI_OCR_CONFIGURATION.md`
- `BHARATHI_INVOICE_DUPLICATE_POLICY.md`
- `BHARATHI_TALLY_READONLY_POC.md`
- This file