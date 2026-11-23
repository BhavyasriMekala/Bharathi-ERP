# Bharathi Test Report

## 2026-11-23 local recovery

| Suite | Result | Notes |
|-------|--------|-------|
| `test_bharathi_bill_workflow.py` | PASS | Supervisor upload → submit → Accountant verify; Supervisor denied verify |
| `test_bharathi_bills.py` | PASS | |
| `test_bharathi_tally_mock.py` | PASS | |
| `GET /health` | PASS | SQLite dev session |
| `GET /health/db` | PARTIAL | Depends on DB connectivity/migrations |
| `npm run build` | PASS | |
| Full pytest suite | NOT RUN | |
| Alembic on Bharathi PG | NOT RUN | Docker unavailable |

## How to re-run

```powershell
cd backend
$env:ALLOW_SQLITE_RUNTIME="1"
$env:DATABASE_URL="sqlite:///./bharathi_local_dev.db"
$env:JWT_SECRET_KEY="local-dev-bharathi-only-not-for-production-32chars"
python -m pytest tests/test_bharathi_bill_workflow.py tests/test_bharathi_bills.py tests/test_bharathi_tally_mock.py -q
```