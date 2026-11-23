# Bharathi — TallyPrime Integration Feasibility

**Status:** Technical assessment only. **No** live Tally connection was tested in this audit. **No** Tally writes were executed.

---

## Problem statement

TallyPrime runs on a **local office PC**. Bharathi ERP will eventually run on **hosted** infrastructure (Render/Firebase per brief). Direct cloud → LAN Tally access is **not realistic** without a deliberate bridge.

Client needs:

- **Inbound:** masters, vouchers, outstanding, GST-related data  
- **Outbound:** approved purchase invoices as purchase vouchers with acknowledgement and idempotency  
- **Operational:** queue, retries, offline handling, reconciliation  

---

## Tally integration mechanisms (industry practice)

| Mechanism | Summary | Cloud ERP fit | Notes |
|-----------|---------|---------------|-------|
| **Tally HTTP/XML (TallyPrime developer / gateway)** | Tally listens on local port; XML request/response | Requires **local agent** that receives jobs from cloud and calls `localhost:9000` (typical) | Most common for product integrations |
| **TDL / custom reports export** | File-based or ODBC bridges | Batch-oriented | Good for backups, weak for near-real-time |
| **ODBC** | Query Tally data | Read-heavy; Windows-bound | Useful for reconciliation reads |
| **Manual XML files** | Import/export | Fallback | High friction |

**Unverified:** Client’s exact TallyPrime version, licensed developer features, and whether HTTP server is enabled on their PC.

---

## Recommended architecture (proposed)

```
┌─────────────────────┐         HTTPS (outbound)         ┌──────────────────────┐
│ Bharathi ERP API    │ ◄───────────────────────────────── │ Tally Connector      │
│ (hosted)            │   sync jobs, acks, heartbeats    │ (Windows service)    │
│ - sync queue in DB  │                                   │ - polls/subscribes   │
│ - idempotency keys  │ ───────────────────────────────► │ - POST XML to Tally  │
└─────────────────────┘         results / voucher IDs      │   on 127.0.0.1       │
                                                            └──────────────────────┘
```

**Security principles:**

- Connector initiates **outbound** connections only (no public Tally port).
- Mutual authentication: device registration + rotating API token (stored in secrets manager, not repo).
- Least privilege: connector limited to configured company + voucher types.
- Full payload audit in `bharathi_tally_sync_items` (already modeled).

---

## What exists in Bharathi repo today

| Asset | Location | Assessment |
|-------|----------|------------|
| Sync run/item tables | `models/bharathi.py` | **Ready shape** for queue |
| Mock connector | `services/bharathi/tally_connector.py` | **Test double** — replace with real adapter behind interface |
| API trigger | `POST /bharathi/tally/sync` | **Manual**; uses hardcoded dry-run outbound payload |
| Mapping table | `BharathiTallyMapping` | **Unused** — needed for ERP↔Tally keys |
| HR payroll Tally config | `hr` APIs + `PayrollSettings.jsx` | **Separate domain** — do not conflate |
| Integrations stub | `GET /integrations/accounting-software` | **Placeholder** |

**Gap:** No Windows agent code in repository; no XML schema mapping for purchase vouchers; no linkage from `VERIFIED` bill to outbound payload.

---

## Sync modes (proposed)

| Mode | Use case | Risk |
|------|----------|------|
| **Manual** | Accountant triggers “Sync now” | Low; good for PoC |
| **Scheduled** | Every N minutes when Tally open | Medium |
| **Near-real-time** | Webhook/event after approval | Higher; needs reliable agent |

**Offline Tally:** Queue items stay `pending`; connector backs off; UI shows last successful cursor (`cursor_before/after` fields exist on sync runs).

---

## Idempotency & duplicate prevention

**Inbound:** Use Tally voucher GUID + voucher number + type as natural key; store in `bharathi_tally_mappings` and sync item `idempotency_key` (pattern already in mock).

**Outbound:** Generate idempotency key from `bharathi_bill_submission.id` + approval revision; on success store `tally_voucher_key`; retries must not create second voucher.

**Conflicts:** If Tally voucher edited/deleted — mark sync item `conflict`, surface in Reconciliation UI; never auto-loop.

---

## Authoritative source matrix (proposed — client to confirm)

| Data | Authoritative (proposal) | ERP role |
|------|--------------------------|----------|
| Supplier master (post go-live) | Tally | ERP cache + mapping |
| Approved purchase invoice (scanned) | ERP until pushed | Push creates Tally voucher |
| Payments / receipts | Tally | Read-only mirror |
| Outstanding / bill-wise | Tally | Dashboard read |
| Sales invoices | Tally | Read-only reports |
| GL balances | Tally | ERP does not re-ledger |

---

## Proof-of-concept plan (safe)

1. **Client provides** Tally backup company copy on office PC (not production books).  
2. Enable Tally HTTP/XML on test company only.  
3. Build connector **read-only** PoC: pull supplier list + purchase register for one month.  
4. Validate ERP staging tables + mapping UI.  
5. **Second phase:** single purchase voucher push from a **manually entered** test invoice (not AI) with rollback procedure.  
6. Only then connect `VERIFIED` Bharathi bills.

**Label until PoC:** All Tally behavior claims are **UNVERIFIED**.

---

## Feasibility conclusion

| Question | Answer |
|----------|--------|
| Is two-way sync technically feasible? | **Yes**, with local connector — standard pattern |
| Is it implemented? | **No** — mock only |
| Can cloud call Tally directly? | **Not safely/reliably** — requires agent |
| Are DB primitives present? | **Partial** — runs/items/mappings; missing bill→voucher bridge |
| Estimated risk | **High** without client Tally access and accounting sign-off |

See `BHARATHI_PROPOSED_ARCHITECTURE.md` and `BHARATHI_IMPLEMENTATION_ROADMAP.md` for sequencing.