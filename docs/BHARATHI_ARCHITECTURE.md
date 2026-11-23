# Bharathi Architecture

## Roles
- **Admin** — full module catalog including `bharathi_*` modules
- **Accountant** — accounts, sales, procurement, bill verification, collections, Tally status
- **Supervisor** — `bharathi_bills` only (+ documents/settings)

## Bill workflow
```
Supervisor → POST /bharathi/bills → submit → mock OCR → PENDING_VERIFICATION
Accountant → POST /bharathi/bills/{id}/verify → VERIFIED | REJECTED | DRAFT
```

## Tally (mock)
```
ERP → MockTallyConnector → bharathi_tally_sync_runs/items (idempotent keys)
```
Live path requires office **Tally Connector** (outbound-only VPN/WebSocket) — not deployed.

## Storage
Uses existing `stored_files` / S3 pipeline; Bharathi bill files reference optional `stored_file_id`.