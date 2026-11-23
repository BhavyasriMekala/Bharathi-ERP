# Bharathi — Implementation Roadmap

**Prerequisite:** Client approval of audit + answers in `BHARATHI_CLIENT_OPEN_QUESTIONS.md`.

Effort ranges: **S** (1–3 d), **M** (1–2 w), **L** (2–4 w), **XL** (1–2 mo+), team-dependent.

---

## Phase 0 — Audit & confirmation (current)

**Deliverables:** This documentation set; Tally PoC plan; sidebar/nav proposal.

**Reuse:** N/A (analysis only).

**Acceptance:** Stakeholder sign-off on scope, authoritative Tally matrix, and Phase 1 start.

**Effort:** Complete.

**Risks:** Unverified Tally version; parallel `VendorBill` vs Bharathi bills ambiguity.

---

## Phase 1 — Mobile invoice capture, OCR, duplicates, approval

**Deliverables:**

- Supervisor mobile UX: Scan Invoice primary action, upload progress, duplicate warnings
- Real OCR integration (bytes from `StoredFile`)
- Field validation + confidence UI
- Accountant structured review (image + form)
- Supplier-scoped duplicate rules + idempotency
- Status machine through `APPROVED` (rename/clarify vs `VERIFIED`)

**Reuse:**

- `SupervisorBillUpload.jsx`, `fileUploadPipeline.js`, `files_api`
- `bill_service.py`, Bharathi models, `test_bharathi_bills.py`
- `AuditLogService`, verification events

**New:**

- OCR worker/provider implementation
- Invoice line schema + migration
- Duplicate review API + UI page
- Enhanced verification UI

**Frontend:** `/bharathi/bills`, `/bharathi/verification`, new duplicate queue  
**Backend:** extend `bill_service`, new validation module  
**DB:** line items, unique constraints, optional `bharathi_duplicate_review`

**Testing:** API tests, duplicate concurrency test, mobile smoke on 375px viewport, poor-image fixtures

**Dependencies:** OCR vendor choice, extraction schema sign-off  
**Risks:** OCR accuracy on thermal bills; cost of vision API  
**Acceptance:** Supervisor uploads real sample → accountant edits → approve without Tally push

**Effort:** **L** (4–6 weeks)

---

## Phase 2 — Supplier directory, ledgers, financial dashboard

**Deliverables:**

- Supplier list with Tally mapping placeholders
- Supplier detail + transaction history (initially from ERP approved invoices; Tally when sync ready)
- Consolidated payable dashboard with correct period/outstanding separation
- Exports (PDF/Excel) for supplier summary

**Reuse:**

- `VendorManagement.jsx`, `SupplierVendorTracker.jsx`
- `AccountsFinancialDashboardView.jsx` patterns
- `procurement` vendor APIs

**New:**

- `financial-dashboard` service
- Read models for payable KPIs
- Archive/restore supplier UX

**Testing:** KPI math unit tests with fixture ledger data  
**Dependencies:** Phase 1 approved invoices in DB  
**Risks:** Wrong outstanding if calculated before Tally feed  
**Acceptance:** Dashboard matches manually verified spreadsheet for test month

**Effort:** **L** (3–5 weeks)

---

## Phase 3 — Tally connector, sync, reconciliation

**Deliverables:**

- Windows connector PoC → production-hardened agent
- Inbound: suppliers, purchases, payments, outstanding
- Outbound: approved purchase voucher with ack + idempotency
- Sync UI: dashboard, history, failed, reconciliation
- Mapping admin for ERP↔Tally keys

**Reuse:**

- `tally_connector.py` interface, sync tables, `TallySyncPanel.jsx`
- `BharathiTallyMapping`, sync run/items

**New:**

- Connector repository (separate binary/installer)
- XML mapping templates
- Job queue API for connector
- Bridge `APPROVED` bill → outbound job

**Testing:** Mock XML golden files; integration test with Tally test company (**manual**); dry-run in CI

**Dependencies:** Office PC access, Tally test company, accounting user for sign-off  
**Risks:** **Highest** project risk; voucher type mismatch; GST rules  
**Acceptance:** One approved scan → one Tally voucher → re-sync does not duplicate

**Effort:** **XL** (6–10+ weeks)

---

## Phase 4 — Sales reports & material analytics

**Deliverables:**

- Sales overview from Tally mirror
- Customer-wise monthly/yearly charts
- Material-wise purchase search API + UI

**Reuse:**

- Reports engine, chart components, procurement line data

**New:**

- Material normalization table (aliases)
- Search API with filters

**Dependencies:** Phase 3 inbound sync  
**Effort:** **M** (2–3 weeks)

---

## Phase 5 — NL queries & optional enhancements

**Deliverables:**

- Allowlisted English queries with citations
- Optional Telugu intents
- WhatsApp/email only if client confirms

**Reuse:**

- Agent infrastructure with strict routing guard

**New:**

- Template catalog + Bharathi-specific intent router

**Dependencies:** Stable dashboard APIs  
**Effort:** **M–L** (3–5 weeks)

---

## Cross-cutting workstreams (parallel)

| Workstream | When |
|------------|------|
| Wire `filterSidebarForBharathi` + proposed nav | Phase 1 start |
| RBAC: `permissions.js` + route modules for `bharathi_*` | Phase 1 |
| Production auth hardening (disable demo login) | Before any hosted deploy |
| PWA manifest + icons | Phase 1 |
| Resolve `VendorBill` vs Bharathi bill strategy | Phase 0 answers |

---

## Recommended sequence rationale

Tally (Phase 3) depends on **approved invoice shape** (Phase 1) and **reporting expectations** (Phase 2). OCR before Tally avoids posting bad data. Sales/materials after Tally inbound data exists.

**S alternative:** If client urgently needs Tally **read-only** dashboard, swap Phase 2 and Phase 3 partial (inbound-only PoC before OCR prod).

---

## Suggested first development phase after approval

**Phase 1** — highest client value, reuses most existing Bharathi code, de-risks OCR before accounting integration.