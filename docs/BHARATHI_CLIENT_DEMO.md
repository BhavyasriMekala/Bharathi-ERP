# Bharathi Enterprises ERP — Client demo guide

Updated: 2026-11-23 · **Demo-first** (no production migration required for rehearsal)

## Critical database note

| Database | Alembic | Demo purchase-invoice APIs |
|----------|---------|----------------------------|
| `bharathi_erp` | `b0a1r2a3t4h5i` | **Broken** until Phase 1 columns exist (`b1p1h2a3s4e5`) |
| `bharathi_migration_test` | `b1p1h2a3s4e5` | **Ready** — use for client demo |
| `bharathi_migration_test_fresh` | `b1p1h2a3s4e5` | **Ready** — empty alternative |

The application code expects Phase 1 invoice header fields (`supplier_name`, `invoice_number`, line items, OCR jobs). Running the UI against `bharathi_erp` at `b0a1r2a3t4h5i` will return SQL errors on bill list/dashboard.

**Do not** run `alembic upgrade head` on `bharathi_erp` without explicit operator approval.

### Safe isolated demo connection

For this session only (does not change committed `.env`):

```powershell
$env:BHARATHI_DEMO_DATABASE = "bharathi_migration_test"
# Point the API at the demo database (same credentials, different DB name):
$env:DATABASE_URL = "postgresql+psycopg://bharathi_user:<password>@127.0.0.1:5432/bharathi_migration_test"
```

Use `DATABASE_PASSWORD` in `.env` with URL-encoding if the password contains special characters.

Verify:

```powershell
cd backend
python scripts/check_bharathi_demo_readiness.py
```

Expect: `DEMO_READY=PASS db=bharathi_migration_test rev=b1p1h2a3s4e5`

## One-time demo setup (isolated DB)

```powershell
cd C:\Users\satee\OneDrive\Desktop\Bharathi-Enterprises-ERP\backend
$env:BHARATHI_DEMO_DATABASE = "bharathi_migration_test"
$env:DATABASE_URL = "postgresql+psycopg://bharathi_user:<password>@127.0.0.1:5432/bharathi_migration_test"

python scripts/setup_local_demo_users.py
python scripts/seed_bharathi_demo_purchase_invoices.py
```

Seed is **idempotent** (markers `bharathi-demo-fiction-20261123-*`). Fictional GSTINs and suppliers only — not client financial data.

OCR for live demos:

```powershell
$env:BHARATHI_OCR_PROVIDER = "mock"   # reliable offline demo
# Optional: BHARATHI_OCR_PROVIDER=openai + OPENAI_API_KEY for real extraction smoke test
```

## Local startup

**Terminal 1 — backend**

```powershell
cd backend
# use demo DATABASE_URL as above when rehearsing
$env:BHARATHI_OCR_PROVIDER = "mock"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — frontend**

```powershell
cd frontend
$env:VITE_BHARATHI_CLIENT = "true"
npm run dev
```

Open: http://localhost:5173

## Demo login (local only)

Requires in `backend/.env`:

- `ENVIRONMENT=development`
- `ENABLE_LOCAL_DEMO_LOGIN=true`
- `LOCAL_DEMO_PASSWORD` (12+ chars; **not** committed)
- `FRONTEND_BASE_URL=http://localhost:5173`

| Role | Login screen email selector | Backend account |
|------|----------------------------|-----------------|
| Admin | Admin | `demo-admin@bharathi.local` |
| Accountant | Accountant | `demo-accountant@bharathi.local` |
| Supervisor | Supervisor | `demo-supervisor@bharathi.local` |
| Store Manager | Store Manager | `demo-storemanager@bharathi.local` |

Use the Bharathi login role dropdown plus shared demo email (`LOCAL_DEMO_UI_EMAIL`, default `demo@bharathi.local`) and `LOCAL_DEMO_PASSWORD` from `.env`.

## Demo routes

| Step | Route | Role |
|------|-------|------|
| Bharathi dashboard | `/bharathi/dashboard` | Admin, Accountant |
| Scan / upload | `/bharathi/bills` | Supervisor |
| OCR review & correction | `/bharathi/verification` | Accountant |
| Purchase register | `/bharathi/register` | Admin, Accountant |
| Supplier-wise summary | `/bharathi/suppliers` | Admin, Accountant |
| Invoice detail | `/bharathi/invoices/:id` | All with `bharathi_bills` |
| Tally read-only PoC | `/bharathi/tally` | Admin, Accountant |
| Collections (legacy KPI) | `/bharathi/collections` | Optional |

## 10-minute client walkthrough

1. **(0:00–1:30) Supervisor — mobile capture**  
   Log in as **Supervisor** → lands on **Scan Invoice** → **Scan invoice** or **Upload file** → optional vendor hint → **Submit for OCR** → show new row in list (mock OCR fills supplier, lines, totals).

2. **(1:30–4:00) Accountant — review & correct**  
   Log out → **Accountant** → **Accounting** dashboard (`/accounts/dashboard`) plus **Pending Verification** under Bharathi links → select seeded or new invoice → edit supplier / invoice # / line grid → **Save corrections** → **Verify** → mention supplier-scoped duplicate warning on `HF-2024-78` style rows.

3. **(4:00–5:00) Approve**  
   **Approve** on verified invoice → status **APPROVED** → audit trail visible.

4. **(5:00–6:30) Register & supplier view**  
   **Purchase Invoice Register** → filter **APPROVED** → open invoice detail → **Supplier Invoices** → show 12 fictional suppliers and approved INR totals.

5. **(6:30–8:00) Dashboard KPIs**  
   **Bharathi Dashboard** → pending approvals, approved amount, supplier snapshot table.

6. **(8:00–10:00) Tally (read-only)**  
   **Tally Sync** → fixture company, supplier ledgers, purchase vouchers → **Dry-run inbound/outbound** only — **no live Tally writes**.

**Store Manager**: inventory-focused nav only (no invoice approval).

## Tests executed (this pass)

```text
pytest tests/test_bharathi_*.py  → 23 passed (includes supplier summary)
vitest src/config/bharathiClient.test.js → passed
npm run build → success
```

## Remaining blockers for production `bharathi_erp` demo

1. Operator approval to apply `b1p1h2a3s4e5` on `bharathi_erp`, **or** keep using `bharathi_migration_test` for client meetings.
2. Live OpenAI OCR not verified in this environment (`BHARATHI_OCR_PROVIDER=mock` recommended for demos).
3. Full `npm test` may still report one legacy `sidebarNav.jobCards` ordering test unrelated to Bharathi.

## Protected databases

Do not modify `insights_iva`, `smrt_db`, or other non-Bharathi databases during demo prep.