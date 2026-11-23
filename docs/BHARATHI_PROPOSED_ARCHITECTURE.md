# Bharathi — Proposed Target Architecture

**Type:** Proposed design. Not implemented in this audit phase.

---

## System context

```
                    ┌─────────────────────────────────────────┐
                    │           Bharathi ERP (hosted)           │
                    │  React SPA  │  FastAPI  │  PostgreSQL   │
                    └──────┬──────────────┬──────────────┬──────┘
                           │              │              │
         Supervisors       │              │              │  Tally Connector
         Accountants   HTTPS│         JWT  │         jobs │  (Windows, office)
         Admin        ──────┘              │              └──────► TallyPrime
                                          │
                                    OCR provider (hosted API)
```

---

## Core domain modules (target)

| Module | Responsibility |
|--------|----------------|
| **Purchase Invoices** | Scan, extract, validate, duplicate check, approve |
| **Suppliers** | Mirror of Tally masters + archive + mapping |
| **Supplier Ledgers** | Read model from Tally (+ ERP pending push) |
| **Financial Dashboard** | Payables KPIs with correct period math |
| **Tally Sync** | Queue, agent, reconciliation |
| **Sales Insights** | Tally read-only aggregates |
| **Materials** | Line-item search across purchases |
| **Administration** | Users, RBAC, settings, audit |

Legacy ERP modules remain in codebase but are **hidden** from Bharathi navigation.

---

## Purchase invoice pipeline (target)

```
DRAFT (uploaded)
  → EXTRACTING (OCR job)
  → EXTRACTED (await review)
  → PENDING_APPROVAL
  → APPROVED
  → SYNC_PENDING → SYNCED | SYNC_FAILED
```

**Today:** `DRAFT` → submit → `PENDING_VERIFICATION` → `VERIFIED` (stops); `POSTED/SYNC_*` enums exist but unused.

**Reuse:** `bill_service`, `BharathiBill*`, `stored_files`, verification events.

**Add:** Line-item table, supplier FK, extraction job worker, structured review DTO, hard duplicate rules.

---

## OCR architecture (proposed)

1. On submit, enqueue job with `stored_file_id`(s).
2. Worker loads bytes (local disk/S3 per `StoredFile`).
3. Provider: pluggable (`mock` dev, `openai_vision` or dedicated invoice API prod).
4. Persist `extracted_json`, `confidence_json`, per-field warnings.
5. **Never** auto-approve solely on AI output.

**Mobile:** Single route `/purchases/scan` (or `/bharathi/bills`) with primary button opening `capture="environment"` + fallback upload.

---

## Duplicate prevention (proposed)

| Layer | Rule |
|-------|------|
| **File** | SHA-256 match → block or force “duplicate override” with reason |
| **Business** | Unique `(tenant_id, supplier_key, invoice_number)` |
| **GSTIN** | Secondary key when supplier resolved |
| **Heuristic** | Same supplier, ±N days, same total → review queue |
| **Tally import** | Match against `tally_voucher_key` / voucher number |
| **Concurrency** | DB unique constraints + idempotency on approve |

---

## Supplier ledger read model (proposed)

- **Inbound sync** writes to `bharathi_tally_*` staging or dedicated `tally_ledger_entries` read tables (migration TBD).
- ERP **does not** recalculate GL independently for payables dashboard.
- UI: Supplier detail = master + running balance from Tally + pending ERP invoices not yet synced.

---

## Consolidated dashboard (proposed)

**API:** `GET /bharathi/financial-dashboard?from&to&grain`

**Metrics computation:**

- `period_purchases` = sum purchase vouchers in period (Tally-sourced)
- `period_payments` = payment vouchers in period
- `outstanding_payables` = Tally outstanding as-of date (not derived from period subtraction)
- `overdue` = bills past due date per Tally bill-wise data

**Reuse:** Chart components from accounts dashboard; new aggregation service.

---

## Tally connector (proposed)

- **Service account** per office installation
- Polls `GET /api/tally/connector/jobs` or MQTT/WebSocket (decision in PoC)
- Executes XML templates per job type
- Reports result + voucher identifiers
- Heartbeat when Tally unreachable

**Maps:** `BharathiTallyMapping` for supplier GUID, voucher type, company name.

---

## Natural language queries (proposed)

- Layer **above** SQL: intent classifier → template ID → parameterized query
- Templates: `material_purchase_total`, `supplier_outstanding`, `monthly_purchase_trend`, etc.
- RBAC: filter suppliers/materials by user permissions
- Response: narrative + table of source rows (invoice IDs, voucher numbers)
- Telugu: optional second locale for intents (**NEEDS CLIENT CONFIRMATION**)

**Do not** expose general-purpose agent SQL on financial data.

---

## Sidebar (proposal — not deployed)

```
Dashboard
Supplier Ledgers
  Summary | All Suppliers | Pending Payments | Archived
Purchases
  Scan Invoice | Register | Material-wise | Duplicate Review | Approval Queue
Sales
  Overview | Customer-wise
Tally Integration
  Sync Dashboard | History | Failed | Reconciliation
Reports
Administration
  Users | Roles | Settings
```

**Implementation note:** Map to existing routes where possible (`/bharathi/*`, `/procurement/vendors`, `/accounts/dashboard`) and add aliases; wire `filterSidebarForBharathi`.

---

## Database additions (recommended — not migrated in audit)

| Table (conceptual) | Purpose |
|--------------------|---------|
| `bharathi_purchase_invoice_lines` | Normalized line items |
| `bharathi_supplier_tally_link` | Or extend `bharathi_tally_mappings` |
| `bharathi_duplicate_review` | Heuristic hits |
| `tally_ledger_snapshot` / `tally_voucher_mirror` | Inbound read model |
| Unique indexes on invoice business keys | Integrity |

Existing `bharathi_*` tables remain foundation.

---

## Security architecture

- Tenant isolation (unchanged)
- Invoice upload: Supervisor module + ownership on files
- MIME/size validation on `files_api` (extend allowed types list if needed)
- Malware scan hooks via existing uploader patterns (**verify enabled in prod**)
- Connector auth: short-lived tokens, IP allowlist optional
- Audit: sync + approval + duplicate override events
- Disable local demo login in production deployment checklist (`BHARATHI_DEPLOYMENT_CHECKLIST.md`)

---

## Hosting (future)

- **API + DB:** Render (per brief)
- **Static SPA:** Firebase Hosting or Render static
- **Files:** S3-compatible object store (existing pipeline)
- **Connector:** Windows service on Bharathi office PC

**Unverified:** Render ↔ connector networking details.