#!/usr/bin/env python3
"""Create Bharathi ERP PostgreSQL role and database on a local PostgreSQL server.

Does not use Insights IVA credentials. Requires PostgreSQL superuser access on your machine.

Usage (PowerShell, from backend/):
  $env:POSTGRES_ADMIN_PASSWORD = "your-postgres-install-password"
  python scripts/setup_bharathi_postgres_local.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


def main() -> int:
    import psycopg
    from psycopg import sql

    admin_user = _env("POSTGRES_ADMIN_USER", "postgres")
    admin_host = _env("POSTGRES_ADMIN_HOST", "127.0.0.1")
    admin_port = _env("POSTGRES_ADMIN_PORT", "5432")
    admin_password = os.environ.get("POSTGRES_ADMIN_PASSWORD", "")
    if not admin_password:
        print("Set POSTGRES_ADMIN_PASSWORD to your local PostgreSQL superuser password.")
        return 1

    app_user = _env("APP_DB_USER", "bharathi_user")
    app_password = _env("APP_DB_PASSWORD", "bharathi_dev")
    app_db = _env("APP_DB_NAME", "bharathi_erp")

    conninfo = (
        f"postgresql://{admin_user}:{admin_password}@{admin_host}:{admin_port}/postgres"
    )
    with psycopg.connect(conninfo, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (app_user,))
            if cur.fetchone():
                cur.execute(
                    sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(
                        sql.Identifier(app_user),
                        sql.Literal(app_password),
                    )
                )
            else:
                cur.execute(
                    sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(
                        sql.Identifier(app_user),
                        sql.Literal(app_password),
                    )
                )
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (app_db,))
            if not cur.fetchone():
                cur.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(app_db),
                        sql.Identifier(app_user),
                    )
                )
    print(f"Ready: postgresql+psycopg://{app_user}:****@{admin_host}:55432/{app_db}")
    print("Use port 55432 when using docker-compose.postgres.yml; otherwise use 5432.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())