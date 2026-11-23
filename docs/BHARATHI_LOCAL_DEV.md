# Bharathi local development

## Root cause: `DATABASE_URL is required`

`Settings` loads `backend/.env` (see `app/core/config.py`). If the file is missing or `DATABASE_URL` is empty, uvicorn fails at import time.

## PostgreSQL (recommended)

```powershell
cd backend
docker compose -f docker-compose.postgres.yml up -d
# copy .env.example to .env if needed — defaults target port 55432
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Credentials (dev only): `bharathi_user` / `bharathi_dev` / database `bharathi_erp` on port **55432**.

Without Docker, run `python scripts/setup_bharathi_postgres_local.py` with `POSTGRES_ADMIN_PASSWORD` set (creates Bharathi role/DB only — not Insights credentials).

## SQLite fallback (offline only)

In `backend/.env`:

```
ALLOW_SQLITE_RUNTIME=1
DATABASE_URL=sqlite:///./bharathi_local_dev.db
```

Use for quick API smoke tests; prefer PostgreSQL for Alembic parity and integration tests.

## Frontend

```powershell
cd frontend
# .env: VITE_API_BASE_URL=http://127.0.0.1:8000
npm run dev
```