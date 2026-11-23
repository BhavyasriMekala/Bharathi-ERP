# Bharathi — Questions for Client Confirmation

Use this list in the next requirements workshop. Answers should be recorded in this file or meeting minutes.

---

## Scope & priorities

1. Confirm **first release** must include live Tally sync, or is OCR + approval + ERP storage acceptable while Tally read-only PoC runs in parallel?
2. Is **Collections / follow-up** module (`/bharathi/collections`) in scope, or strictly **accounts payable** to suppliers?
3. Should **procurement PO / MR / GRN** flows remain accessible to anyone, or hidden entirely for all Bharathi users?
4. Confirm **~40 suppliers** — static list or frequent onboarding? Who maintains master data (Tally vs ERP)?

---

## Purchase invoices

5. After approval, should the invoice appear only in ERP, only in Tally, or **both** with ERP as draft until push succeeds?
6. Who can **approve** — Accountant only, or Admin as well? Two-step approval needed?
7. Required **invoice fields** when OCR missing — block submit or allow partial with mandatory manual fill?
8. Acceptable **OCR providers** (cloud vision vs on-prem)? Data residency / privacy constraints?
9. Retention period for **original images/PDFs**?

---

## Duplicates

10. On exact duplicate (same file): **block** or **allow override** with reason?
11. On same supplier + invoice number: reject automatically or route to **Duplicate Review** queue?
12. Should duplicates against **Tally-imported** vouchers block ERP approval?

---

## TallyPrime

13. Exact **TallyPrime version** and license (Silver/Gold, multi-user count)?
14. Is **Tally HTTP/XML** enabled today, or willing to enable on a **test company**?
15. Which **voucher types** for purchase entry (Accounting Invoice, Item Invoice, etc.)?
16. **Company name** and financial year start for mapping?
17. Who will install and maintain the **Windows connector** (IT vendor, internal staff)?
18. Expected sync frequency: manual, hourly, daily?
19. For **two-way** sync: confirm Tally remains authoritative for payments and outstanding.
20. GST: intra-state (CGST/SGST) vs IGST rules — any special cases?

---

## Suppliers & ledgers

21. Define **payable vs receivable** for suppliers who also buy scrap/returns from you.
22. **Opening balances** — import once from Tally at cutover date?
23. **Archive supplier** — can they still receive new invoices if Tally shows activity?
24. Ledger export format preference (PDF, Excel, both)?

---

## Dashboard & reporting

25. Confirm **fiscal year** vs calendar filters.
26. Which **KPIs** are mandatory for go-live vs nice-to-have?
27. **Material naming** — do suppliers use different descriptions for the same item (alias list needed)?
28. **Unit conversions** (kg vs bundle) — required in v1?

---

## Sales

29. Confirm sales data is **Tally-only** with no ERP sales invoicing for Bharathi users.
30. List of **~5 regular customers** — any privacy labeling in reports?

---

## Natural language

31. **Telugu** support required in v1 or phase 2?
32. Which **3–5 sample questions** must work on day one (acceptance test)?

---

## Users & security

33. **Phone OTP login** required, or email/password sufficient initially?
34. Number of **Supervisor** devices concurrently?
35. **Admin** users count and whether external auditor read-only role is needed.
36. Confirm **no shared demo password** in production (dev-only feature today).

---

## Technical environment

37. Office **internet** reliability for connector; static IP or dynamic DNS?
38. Planned **Render/Firefox** regions and file storage (S3 bucket jurisdiction)?
39. Existing **backup** process for Tally data before first sync test?

---

## Optional features

40. Enable **WhatsApp** alerts for approvals or overdue payables?  
41. **Employee expense** categories in scope for 2026?

---

## Decisions log (fill after meeting)

| # | Question | Answer | Date |
|---|----------|--------|------|
| | | | |