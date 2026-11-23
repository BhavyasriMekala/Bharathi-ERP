# Bharathi Enterprises — Client Requirements (Meeting Capture)

**Status:** Confirmed priorities from client meeting (as relayed in project brief). Items marked **NEEDS CLIENT CONFIRMATION** require explicit sign-off before build.

**Distinction:** This document is **requirements**, not implementation status. See `BHARATHI_EXISTING_ERP_AUDIT.md` and `BHARATHI_FEATURE_GAP_ANALYSIS.md` for codebase reality.

---

## Confirmed client priorities

The client wants a **focused** ERP, not a full manufacturing suite. Highest priority:

1. **AI purchase invoice scanning** — receive supplier invoices (not internal PO creation).
2. **Automatic extraction** of supplier, GSTIN, invoice metadata, line items, taxes, totals.
3. **Duplicate invoice detection** — supplier-scoped, not invoice-number-only.
4. **~40 supplier ledgers** — primarily sourced from **TallyPrime**.
5. **Consolidated financial dashboard** — payables, purchases, payments, trends (period-correct accounting).
6. **Two-way TallyPrime sync** — avoid double entry; idempotent voucher push after human approval.
7. **Minimal sales reporting** from Tally (small customer base).
8. **Mobile-friendly** invoice capture (PWA/responsive web acceptable).
9. **Role-based access** — Admin, Accountant, Supervisor (configurable).
10. **Material-wise purchase history** and intelligent search.

---

## AI purchase invoice workflow (required)

| Step | Requirement |
|------|-------------|
| 1 | Supervisor logs in on mobile |
| 2 | Opens Purchase Invoices module |
| 3 | Single **Scan Invoice** action |
| 4 | Camera opens where browser allows |
| 5 | Capture photo or upload JPG/PNG/PDF |
| 6 | AI/OCR processes document |
| 7 | Extract fields (supplier, GSTIN, invoice no/date, materials, HSN, qty, UOM, rates, taxable, CGST/SGST/IGST, charges, discount, total, currency, payment terms) |
| 8 | Validate extraction; show confidence and warnings |
| 9 | Duplicate check before approval |
| 10 | Review and correct in UI |
| 11 | Submit for approval |
| 12 | Store validated invoice in ERP after approval |
| 13 | Sync to Tally only after approval — never auto-post unverified AI output |

**Rules:** Do not invent missing data; preserve original file; audit trail; no duplicate accounting entries.

---

## Duplicate detection (required)

- Same supplier + invoice number
- Supplier GSTIN + invoice number
- Date + amount heuristics
- Document fingerprint (hash)
- Conflict review for near-duplicates
- Reconciliation with Tally-imported vouchers
- Reject exact duplicates; flag potential duplicates
- Concurrency-safe (no double approved records)

---

## Supplier-wise ledgers (required)

- Directory, search, detail page, per-supplier ledger
- Purchases, payments, credit notes, opening/closing balance, pending payable
- Date filters, exports, archive inactive suppliers (no delete of history)
- **Primary source: Tally** — ERP ledger must reconcile, not compete blindly
- Distinguish payable vs receivable per Tally debit/credit conventions

---

## Consolidated dashboard (required)

Metrics: period purchases, payments, outstanding payables, overdue, unpaid/paid counts, supplier-wise outstanding, purchase/payment trends, material spend, largest outstanding suppliers.

Date filters: weekly, biweekly, monthly, quarterly, yearly, custom range.

**Accounting rule:** Outstanding ≠ (period purchases − period payments). Use opening + movements + closing.

---

## TallyPrime integration (required — critical)

**Direction A — Tally → ERP:** Masters, ledgers, purchase/sales/payment/receipt vouchers, notes, outstanding, bill-wise allocations, GST.

**Direction B — ERP → Tally:** After verify + approve → prepared voucher → push → Tally ack → store voucher id → no re-sync duplicates.

**Constraints (confirmed for design):**

- Tally typically on **local office PC** — cloud cannot assume direct LAN access.
- Prefer **local connector/agent** with outbound secure channel.
- Do not expose Tally HTTP to public internet.
- Queue, retries, idempotency, conflict handling, offline Tally, sync status UI.

**Not in scope for audit phase:** Live Tally writes or production accounting changes.

---

## Sales reporting (required, lightweight)

- Monthly/yearly totals, customer-wise sales, trends, Tally visibility, date filters, downloads
- **Do not** build full sales invoicing unless client confirms

---

## Material-wise purchase history (required)

Search by material, supplier, date, qty, unit, price range, financial year; normalization and alias handling.

---

## Natural-language query (required)

English (and optionally Telugu) questions over **authorized** data; templated/allowlisted queries only; show sources; no hallucinated figures; no unrestricted AI SQL.

---

## Mobile-first web (required)

Android Chrome, iPhone Safari, responsive ledger/dashboard, large touch targets, camera + upload fallback, progress, duplicate warnings, minimal Supervisor path.

---

## Roles (required)

| Role | Intent |
|------|--------|
| Admin | Users, roles, settings, suppliers, approvals, sync status |
| Accountant | Financial review, ledgers, reports, sync (if permitted) |
| Supervisor | Capture/upload, own status, limited edits |

Configurable modules and actions; audit history; deactivate users without erasing history.

**Production auth:** Local demo login is dev-only (see `BHARATHI_LOCAL_DEV.md`).

---

## Optional / future (not first-release confirmed)

Employee expenses, travel/food allowances, extra GST packs, WhatsApp, email alerts, native app, advanced analytics — classify as **OPTIONAL** until client confirms.

---

## Assumptions (proposal — needs validation)

- Single tenant (Bharathi Enterprises) on `bharathi_erp`.
- TallyPrime version supports XML/HTTP or approved connector pattern (**UNVERIFIED** in repo).
- ~40 suppliers manageable with Tally master sync.
- Supervisor workflow is primary mobile use case.

---

## Document map

| Document | Purpose |
|----------|---------|
| `BHARATHI_EXISTING_ERP_AUDIT.md` | What the fork already contains |
| `BHARATHI_FEATURE_GAP_ANALYSIS.md` | Requirement vs evidence table |
| `BHARATHI_TALLY_INTEGRATION_FEASIBILITY.md` | Tally technical options |
| `BHARATHI_PROPOSED_ARCHITECTURE.md` | Target design |
| `BHARATHI_IMPLEMENTATION_ROADMAP.md` | Phased delivery |
| `BHARATHI_CLIENT_OPEN_QUESTIONS.md` | Decisions pending client input |