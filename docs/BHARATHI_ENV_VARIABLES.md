# Bharathi Enterprises ERP — Environment variables

See `backend/.env.example` and `frontend/.env.example`. Never commit real `.env` files.

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | Yes | `postgresql+psycopg://...@.../bharathi_erp` — local Docker uses port **55432** |
| `JWT_SECRET_KEY` | Production | Min 32 chars |
| `CORS_ORIGINS` | Production | Bharathi SPA origins only |
| `ALLOWED_HOSTS` | Production | Render hostname + app domain |
| `STORAGE_PROVIDER` | Production | `s3` with dedicated bucket |
| `VITE_API_BASE_URL` | Hosted SPA | Bharathi API URL; empty for same-origin proxy |
| `OPENAI_API_KEY` | Optional | Vision OCR — BLOCKED EXTERNAL until configured |
| Tally connector URL | Optional | Office-side connector — BLOCKED EXTERNAL |