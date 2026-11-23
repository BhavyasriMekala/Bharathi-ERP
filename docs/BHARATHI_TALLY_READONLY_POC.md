# Bharathi TallyPrime read-only PoC

## Scope

- **In scope:** read-only connector interface, fixture supplier ledgers and purchase vouchers, company identity mapping, decimal-safe amounts, duplicate import identity keys (design only), automated tests.
- **Out of scope:** live Tally ODBC/XML-RPC, voucher create/update/delete, pushing ERP data into Tally.

## Architecture (target production path)

1. **ERP (cloud):** `GET /bharathi/tally/readonly-poc` and future read endpoints — no write APIs.
2. **Windows local connector (future):** small service on the office PC that queries Tally in read-only mode and exposes results to the ERP over a authenticated channel. Not shipped in Phase 1.

## Current implementation

- Python: `backend/app/services/bharathi/tally_readonly_connector.py`
- Mock connector returns fixture company, ledgers, and purchase vouchers.
- `UnavailableTallyReadOnlyConnector` is returned when `use_mock=False` (not connected).
- XML helper `parse_tally_ledger_xml()` parses minimal ledger export fixtures for tests.

## API

`GET /api/bharathi/tally/readonly-poc` (requires `bharathi_tally` permission)

Response includes `mode`, `live_tally: false`, `writes_disabled: true`, and fixture data. UI: **Tally synchronization** page loads this on mount.

## Verification

```bash
cd backend
pytest tests/test_bharathi_phase1.py tests/test_bharathi_tally_mock.py -q
```

Live Tally verification is **not** performed until the Windows connector is approved and installed.