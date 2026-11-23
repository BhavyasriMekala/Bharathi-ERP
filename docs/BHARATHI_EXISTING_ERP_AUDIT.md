# Bharathi Enterprises — Existing ERP Audit

**Repository:** `C:\Users\satee\OneDrive\Desktop\Bharathi-Enterprises-ERP`  
**Audit date:** 2026-11-23  
**Method:** Static code review, existing tests referenced (`tests/test_bharathi_bills.py`, `test_bharathi_tally_mock.py`, `test_local_demo_login.py`). **No** migrations run; **no** live Tally connectivity verified.

---

## Executive snapshot

This codebase is an **Insights IVA ERP fork** with a **Bharathi vertical slice** (`bharathi_*` tables, APIs, four frontend pages). The full manufacturing/commerce ERP (production, HR, inventory, sales, procurement, accounts) remains present.

**Bharathi-specific maturity:**

| Area | Status |
|------|--------|
| Bill upload + stored files + submit → mock OCR | **Partially working** (mock OCR, no real vision) |
| Accountant verify / reject / correction | **Partially working** |
| Duplicate file SHA link | **Partial** (flags `duplicate_of_id`, does not block) |
| Tally sync | **Placeholder** (mock connector, dry-run UI) |
| Supplier ledger from Tally | **Not implemented** |
| Client financial dashboard | **Partial** (generic accounts dashboard exists; not Bharathi-consolidated payable view) |
| NL financial Q&A | **Partial** (generic ERP AI agent, not purchase/Tally-safe templates) |

---

## Bharathi backend (evidence)

### API router

- **File:** `backend/app/api/bharathi_api.py`
- **Prefix:** `/bharathi` and `/api/bharathi` (dual mount in `main.py`)
- **Endpoints:** company profile ensure, dashboard KPIs, bills CRUD, submit, verify, collections outstanding, vendor price compare (in-memory), `POST /tally/sync`

### Services

| File | Role | Maturity |
|------|------|----------|
| `services/bharathi/bill_service.py` | DRAFT → submit → OCR → PENDING_VERIFICATION → verify → VERIFIED | Real DB; stops at VERIFIED |
| `services/bharathi/ocr_providers.py` | `MockOcrProvider`; `OpenAIVisionOcrProvider` raises `NotImplementedError` | Mock only |
| `services/bharathi/tally_connector.py` | `MockTallyConnector`, sync run/item persistence | Mock only |
| `services/bharathi/dashboard_service.py` | Bill counts by status | Basic KPI |
| `services/bharathi/collections_service.py` | Aging on `BharathiCollectionFollowUp` | Not full AR from Tally |
| `services/bharathi/vendor_pricing_service.py` | Landed cost compare | No DB persistence |

### Models / migration

- **Models:** `backend/app/models/bharathi.py`
- **Migration:** `alembic/versions/b0a1r2a3t4h5i_bharathi_foundation.py` (creates `bharathi_*` tables)
- **Statuses in config:** `POSTED`, `SYNC_PENDING`, `SYNCED`, `SYNC_FAILED` in `core/bharathi_client.py` — **not set** in `bill_service.py` (ahead of code)

### Config / RBAC

- `core/bharathi_client.py` — hidden modules list, UI roles, bill statuses
- `core/rbac_constants.py` — modules `bharathi_bills`, `bharathi_tally`, `bharathi_collections` for Admin/Accountant/Supervisor templates
- `core/local_demo_login.py` — development-only shared demo email (not for production)

---

## Bharathi frontend (evidence)

| Route | Component | Notes |
|-------|-----------|-------|
| `/bharathi/bills` | `SupervisorBillUpload.jsx` | `capture="environment"`, presigned upload pipeline |
| `/bharathi/verification` | `AccountantVerificationQueue.jsx` | JSON `<pre>` extraction preview |
| `/bharathi/collections` | `CollectionsDashboard.jsx` | Read-only table |
| `/bharathi/tally` | `TallySyncPanel.jsx` | `dry_run: true` messaging |

- **API client:** `frontend/src/api/bharathiApi.js`
- **Nav:** Bharathi links at top of `config/sidebarNav.js`
- **`filterSidebarForBharathi` in `bharathiClient.js`:** defined but **not wired** in `Sidebar.jsx`
- **Supervisor post-login redirect:** `/bharathi/bills` (`roleRedirect.js`)

---

## Shared ERP modules — classification

Legend: **KEEP** | **CUSTOMIZE** | **HIDE** | **NEW** | **CONFIRM**

| Module / area | Class | Evidence | Notes |
|---------------|-------|----------|-------|
| Bharathi bill capture | **CUSTOMIZE** | `bharathi_*` + UI | Core client path; needs real OCR + UX |
| Auth + JWT + sessions | **KEEP** | `api/auth.py`, `auth_service` | Remove demo login in prod |
| RBAC admin | **KEEP** | `rbac_api`, `admin.py`, seed roles | Map Bharathi modules in UI guards |
| Accounts / GL / AP-AR | **CUSTOMIZE** | `api/accounts.py`, models | Reuse reports; align with Tally source of truth |
| Procurement vendors / `VendorBill` | **CUSTOMIZE** | `api/procurement.py` | Parallel to Bharathi bills — needs bridge or hide PO flow |
| Supplier tracker UI | **CUSTOMIZE** | `SupplierVendorTracker.jsx` | Not Tally ledger |
| Sales invoices module | **HIDE** (nav) | `sales/*` routes | Client wants Tally-sourced sales reports only |
| Production / BOM / WO | **HIDE** | Many routes in `AppRoutes.jsx` | Not client scope |
| HR / payroll / Tally payroll settings | **HIDE** | `hr/*`, `PayrollSettings.jsx` Tally fields | Unrelated to purchase focus |
| Inventory / warehouse | **HIDE** | `inventory/*` | Optional future |
| Quality / maintenance | **HIDE** | routes present | Not client scope |
| Work chat / meetings | **HIDE** | `chat`, `meetings` | Optional |
| Analytics / factory / IoT | **HIDE** | listed in `BHARATHI_HIDDEN_MODULES` | Not applied in Sidebar yet |
| Document library + upload pipeline | **KEEP** | `files_api`, `fileUploadPipeline.js` | Reuse for invoice files |
| Approval queue (admin) | **CUSTOMIZE** | `admin.py` approvals | Does not include Bharathi bills today |
| ERP AI assistant | **CUSTOMIZE** | `StoreAgentChatPanel`, `/api/agent/chat` | Not financial NL with allowlists |
| Audit logs | **KEEP** | `AuditLog`, `AccessLog`, middleware | Bill create logged |
| Integrations stub | **PLACEHOLDER** | `GET /integrations/accounting-software` | Always disconnected |

---

## Authentication & roles (as implemented)

- **Roles seeded:** Admin, Accountant, Supervisor (+ many legacy ERP roles still in DB)
- **Supervisor modules (template):** `dashboard`, `bharathi_bills`, `documents`, `settings`
- **Accountant:** includes `bharathi_bills`, `bharathi_tally`, `bharathi_collections`, `accounts`, `procurement`, `sales`, etc.
- **Frontend `permissions.js`:** Bharathi module codes not in static `MODULES` — relies on API-returned permissions (**gap**)
- **`/bharathi/*` route guard:** falls back to `dashboard` module in path resolver (**gap**)

---

## Duplicate detection (as implemented)

- **File SHA-256:** `bill_service._duplicate_check` sets `duplicate_of_id` on new submission; **does not reject** upload
- **Idempotency key:** returns existing submission if key repeats
- **Tally sync item:** idempotency in `tally_connector`
- **Document library:** name/category duplicate check — separate subsystem
- **No** unique constraint on supplier + invoice number for Bharathi bills

---

## OCR / AI (as implemented)

- Submit calls `get_ocr_provider("mock")` — **does not read file bytes**
- Mock returns deterministic JSON influenced by `vendor_hint`
- OpenAI vision stub not implemented

---

## Tally (as implemented)

- `MockTallyConnector` only
- `BharathiTallyMapping` table — **no service usage found**
- Outbound API uses hardcoded dry-run payload, not verified bills
- HR payroll has separate Tally config API — **not** Bharathi purchase sync

---

## Database (local)

- **Target:** PostgreSQL `bharathi_erp` @ `bharathi_user:5432` (per project brief)
- Bharathi tables via migration `b0a1r2a3t4h5i`
- Full ERP schema (hundreds of tables) from parent product remains

---

## Tests (referenced, not re-run in this audit)

| Test | Indicates |
|------|-----------|
| `test_bharathi_bills.py` | Bill workflow with mock OCR |
| `test_bharathi_tally_mock.py` | Sync run persistence |
| `test_local_demo_login.py` | Dev login only |
| Frontend `npm run build` | Reported passing in `BHARATHI_IMPLEMENTATION_STATUS.md` |

---

## Security notes (observed)

- Tenant-scoped queries on Bharathi entities
- File upload requires completed `StoredFile` + ownership check for supervisors
- Production must disable `ENABLE_LOCAL_DEMO_LOGIN` and remove demo users
- No secrets documented in this file

---

## Unnecessary-for-client surface area (recommend HIDE in nav)

Production planning, BOM, work orders, factory monitor, IoT, HR suite, quality, maintenance, CRM-heavy sales workflow, operator shop floor, platform admin extras — all remain in codebase but should not appear in Bharathi operator experience (`BHARATHI_HIDDEN_MODULES` is the intended filter once wired).