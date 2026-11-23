# Bharathi Deployment Checklist (no auto-provision)

Local dev: see [BHARATHI_LOCAL_DEV.md](./BHARATHI_LOCAL_DEV.md).

- [ ] Create Render service `bharathi-enterprises-api` (new)
- [ ] Create Firebase project + Hosting site placeholders
- [ ] Create PostgreSQL `bharathi_erp`
- [ ] Create S3 bucket + IAM
- [ ] Set all secrets in dashboard (see `docs/BHARATHI_ENV_VARIABLES.md`)
- [ ] Run `alembic upgrade head` on staging DB only
- [ ] Set `VITE_API_BASE_URL` to Bharathi API
- [ ] UAT three roles
- [ ] **Do not** attach Insights IVA credentials or hosts