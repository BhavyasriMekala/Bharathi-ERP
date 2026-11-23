# Bharathi Enterprises — Feature Gap Analysis

Evidence-based comparison. Status labels: **Working** | **Partial** | **Placeholder/UI only** | **Not implemented** | **Not verified**

---

## Gap analysis table

| # | Client requirement | Existing module/component | Backend references | Frontend references | DB models/tables | Current status | Missing functionality | Recommended action | Priority | Complexity | Dependencies |
|---|-------------------|---------------------------|-------------------|---------------------|------------------|----------------|----------------------|-------------------|----------|------------|--------------|
| 1 | Mobile scan/upload purchase invoice | Bharathi bill capture | `api/bharathi_api.py`, `services/bharathi/bill_service.py`, `files_api.py` | `SupervisorBillUpload.jsx`, `fileUploadPipeline.js` | `bharathi_bill_submissions`, `bharathi_bill_files`, `stored_files` | **Partial** | Single “Scan Invoice” CTA; camera UX; PDF multi-page; poor-quality handling | CUSTOMIZE UI + pipeline; rename nav to Purchase Invoices | P0 | M | Files storage |
| 2 | AI/OCR field extraction (full GST invoice) | Mock OCR provider | `ocr_providers.py`, `bill_service.run_ocr` | `AccountantVerificationQueue.jsx` (JSON only) | `bharathi_bill_extractions` | **Placeholder** | Real vision OCR; read image/PDF bytes; HSN/SAC; confidence per field; no hallucination policy | NEW provider integration + extraction schema | P0 | L | OCR vendor/API, file fetch |
| 3 | Extraction validation & warnings | Bill submit/verify | `bill_service.py` | Verification queue | `extracted_json`, `confidence_json` | **Partial** | Business rules, GST math checks, mandatory field gates | NEW validation service | P0 | M | OCR schema |
| 4 | Review/correct before approval | Verification UI | `POST .../verify`, `.../request_correction` | `AccountantVerificationQueue.jsx` | `bharathi_bill_verification_events` | **Partial** | Structured form editor; side-by-side image; line-item grid | CUSTOMIZE frontend + APIs | P0 | M | OCR schema |
| 5 | Approval workflow after review | Bill verify endpoint | `bill_service.verify_*` | Verification queue | status `VERIFIED` | **Partial** | Explicit approve vs verify naming; Admin approval; queue in `/admin/approvals` | CUSTOMIZE workflow + admin queue type | P1 | M | RBAC actions |
| 6 | Post-approval ERP storage | Bharathi submissions | `bill_service` | — | `bharathi_bill_submissions` | **Partial** | Normalized invoice header/lines tables; link to supplier master | NEW/CUSTOMIZE schema + mapping | P0 | M | Data model decision |
| 7 | Duplicate: same file | SHA duplicate link | `_duplicate_check` | — | `content_sha256`, `duplicate_of_id` | **Partial** | Block or require override; UI warning | CUSTOMIZE service + UI | P0 | S | — |
| 8 | Duplicate: supplier + invoice no | — | — | — | — | **Not implemented** | Unique index scoped by tenant+supplier+invoice_no | NEW constraints + check on submit | P0 | M | Supplier master IDs |
| 9 | Duplicate: GSTIN + invoice no | — | — | — | — | **Not implemented** | Same as above with GSTIN | NEW | P0 | M | Master data |
| 10 | Duplicate: amount/date heuristic | — | — | — | — | **Not implemented** | Fuzzy match queue | NEW review module | P1 | M | Historical data |
| 11 | Concurrent upload idempotency | Idempotency key | `create_submission` | Not sent from UI | `idempotency_key` | **Partial** | Client-generated keys; DB unique constraint | CUSTOMIZE API + frontend | P1 | S | — |
| 12 | Preserve original document | File storage | `StoredFile`, `BharathiBillFile` | upload pipeline | FK to `stored_files` | **Working** | Immutable retention policy; download in review UI | CUSTOMIZE UI | P0 | S | Storage config |
| 13 | Audit trail | Audit logs | `AuditLogService`, verification events | — | `audit_logs`, `bharathi_bill_verification_events` | **Partial** | End-to-end sync audit; export | KEEP + extend | P1 | S | — |
| 14 | Supplier directory (~40) | Procurement vendors | `api/procurement.py` `/vendors` | `VendorManagement.jsx`, tracker | `suppliers` (inventory/procurement) | **Working** (ERP) | Bharathi-only fields; Tally GUID; archive flag | CUSTOMIZE master + sync | P1 | M | Tally masters |
| 15 | Supplier ledger from Tally | Accounts GL/AP | `api/accounts.py` | `AccountsPayable`, ledger views | `journal_*`, `vendor_bills` | **Partial** (ERP ledger) | Tally-sourced ledger; opening/closing; payable vs receivable | NEW sync + read models | P0 | L | Tally connector |
| 16 | Archive inactive suppliers | Supplier CRUD | procurement vendors | vendor UI | supplier `is_active` patterns | **Partial** | Explicit archive list + restore permission | CUSTOMIZE | P2 | S | Client rules |
| 17 | Consolidated payable dashboard | Accounts dashboard | `accounts` dashboard API, `bharathi/dashboard` | `AccountsFinancialDashboardView`, (unused `getBharathiDashboard`) | various | **Partial** | Supplier-wise outstanding; period-correct metrics; Bharathi layout | NEW dashboard service + UI | P0 | L | Tally data |
| 18 | Date filters (week/custom) | Dashboard/widgets | analytics/reports partial | multiple dashboard components | — | **Partial** | Unified filter component for Bharathi dash | CUSTOMIZE | P1 | M | Dashboard API |
| 19 | Download ledger/report | Export utilities | reports_engine, PDF utils | various export buttons | — | **Partial** | Supplier ledger PDF/Excel | CUSTOMIZE | P1 | M | Dashboard data |
| 20 | Tally → ERP sync | Mock connector | `tally_connector.py`, `bharathi_api` | `TallySyncPanel.jsx` | `bharathi_tally_sync_*` | **Placeholder** | Real connector; masters & vouchers; scheduling | NEW agent + sync workers | P0 | XL | Office PC agent |
| 21 | ERP → Tally after approve | Mock outbound | `tally_connector.push_voucher` | — | `tally_voucher_key` on items | **Not implemented** | Map VERIFIED bill → purchase voucher; ack + idempotency | NEW | P0 | XL | Approval + mapping |
| 22 | Sync status / failed queue / reconcile | Sync tables | sync run/item models | Tally panel | `bharathi_tally_sync_runs/items` | **Partial** (schema) | UI for failed/retry/reconciliation | NEW UI + services | P0 | L | Connector |
| 23 | Tally mapping ERP↔Tally | Mapping table | model only | — | `bharathi_tally_mappings` | **Not implemented** (unused) | CRUD + sync use | IMPLEMENT service | P0 | M | Connector |
| 24 | Sales reports from Tally | Sales module | `api/sales.py` | sales dashboards | `invoices` | **Working** (ERP sales) | Read-only Tally-imported sales summaries | NEW read API + HIDE ERP sales entry | P2 | M | Tally sync |
| 25 | Material-wise purchase history | Procurement + inventory | procurement, inventory APIs | purchases lists | PO lines, products | **Partial** | Material search across Bharathi/Tally purchases | NEW analytics API | P1 | L | Normalized lines |
| 26 | Natural language financial Q&A | ERP AI agent | `ai_assistant.py`, `v1/agent.py` | `StoreAgentChatPanel.jsx` | — | **Partial** | Allowlisted query templates; Telugu; citations | NEW Bharathi NL layer | P2 | L | Dashboard APIs |
| 27 | Roles Admin/Accountant/Supervisor | RBAC | `rbac_constants.py`, `rbac_api` | Login, Sidebar filters | `roles`, permissions JSON | **Partial** | Wire Bharathi modules in `permissions.js`; route guards | CUSTOMIZE | P0 | S | — |
| 28 | Configurable permissions | Admin roles UI | `admin.py`, RBAC API | settings/admin pages | role permissions | **Working** | Bharathi action granularity (approve, sync push) | CUSTOMIZE | P1 | M | — |
| 29 | Mobile PWA / responsive | App shell | — | `App.jsx`, sidebar drawer | — | **Partial** | PWA manifest; Supervisor bottom nav shortcut | CUSTOMIZE | P1 | M | UX |
| 30 | No double entry with Tally | — | — | — | — | **Not implemented** | Authoritative field matrix | DESIGN in architecture doc | P0 | XL | Client process |
| 31 | Procurement PO workflow | Full procurement | `procurement.py` PO/MR/GRN | many purchase pages | `purchase_orders` | **Working** | Client does not want PO-centric flow | **HIDE** nav | P3 | S | Client confirm |
| 32 | Parallel `VendorBill` module | Procurement bills | `vendor_bills` | `VendorBills.jsx` | `vendor_bills` | **Working** | Consolidate or bridge to Bharathi bills | **CONFIRM** | P1 | L | Data model |
| 33 | Collections follow-up | Bharathi collections | `collections_service.py` | `CollectionsDashboard.jsx` | `bharathi_collection_followups` | **Partial** | Client focus is payables; may be low priority | **CONFIRM** / defer | P3 | M | — |
| 34 | Vendor price compare | Bharathi API | `vendor_pricing_service.py` | not exposed in UI | — | **Placeholder** | Optional client feature | DEFER | P4 | S | — |
| 35 | Production demo login | `local_demo_login.py` | auth routes | Login.jsx roles | demo users script | **Working** (dev only) | Disable in production | OPS (documented) | P0 | S | Deployment |

---

## Summary counts

| Status | Approx. requirements |
|--------|---------------------|
| Working (reuse as-is) | 3 |
| Partial | 18 |
| Placeholder / UI only | 4 |
| Not implemented | 10 |

---

## Reuse highlights

- **Upload pipeline:** `files_api` + `uploadFileThroughPipeline` + virus scan hooks in `FileUploader.jsx`
- **RBAC framework:** roles, admin assignment, audit middleware
- **Procurement supplier master:** starting point for 40 suppliers (needs Tally keys)
- **Accounts reporting engine:** patterns for exports and KPI cards (not Tally-correct yet)
- **Bharathi bill state machine skeleton:** submit/verify with tests

---

## New development (net-new for client)

1. Tally Windows connector agent + secure channel  
2. Real OCR/AI extraction with confidence and validation  
3. Supplier-scoped duplicate engine + review queue  
4. Normalized purchase invoice header/lines post-approval  
5. Tally-sourced supplier ledger + consolidated payable dashboard  
6. Bharathi NL query layer (allowlisted)  
7. Simplified navigation wiring (`filterSidebarForBharathi`)

---

## Hide (retain code)

Production, HR, quality, maintenance, IoT, factory monitor, work chat, meetings, heavy sales CRM, operator flows — per `BHARATHI_HIDDEN_MODULES` in `core/bharathi_client.py`.