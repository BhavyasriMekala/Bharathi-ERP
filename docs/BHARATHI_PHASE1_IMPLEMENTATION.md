# Phase 1 — AI purchase invoice automation (implementation summary)

## Backend

- Models/migration: `b1p1h2a3s4e5_phase1_bharathi_invoice.py` (not applied to production `bharathi_erp` without operator approval).
- Workflow: `invoice_workflow.py`, `bill_service.py`, `bharathi_api.py`.
- OCR: `ocr_providers.py` (mock + OpenAI vision).
- Duplicates: `duplicate_detection.py`.
- Audit: verification events + `GET /bharathi/bills/{id}/audit`.

## Frontend (Bharathi client mode)

| Route | Page |
|-------|------|
| `/bharathi/bills` | Scan / upload invoice (Supervisor) |
| `/bharathi/verification` | Review, correct, verify, approve |
| `/bharathi/register` | Searchable purchase invoice register |
| `/bharathi/tally` | Read-only PoC status + dry-run mock sync |

Nav filtering: `bharathiClient.js`, `Sidebar.jsx`, `permissions.js`.

## RBAC (purchase invoices)

| Action | Admin | Accountant | Supervisor | Store Manager |
|--------|-------|------------|------------|---------------|
| Upload / submit | Yes | Yes | Yes | No (module) |
| Verify / reject | Yes | Yes | No* | No |
| Approve | Yes | Yes | No | No |

\*Supervisor has `bharathi_bills` for upload only; approval enforced server-side via `assert_can_approve`.

## Local verification

1. Backend: `cd backend && pytest tests/test_bharathi_phase1.py tests/test_bharathi_bill_workflow.py tests/test_bharathi_tally_mock.py tests/test_bharathi_bills.py -q`
2. Apply migration on disposable DB or SQLite test harness only until approved for `bharathi_erp`.
3. Frontend: `cd frontend && npm test -- --run && npm run build`