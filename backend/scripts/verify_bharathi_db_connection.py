"""Verify local Bharathi PostgreSQL connection (no secrets printed). Exit 0 on success."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, text

from app.core.config import get_settings
from sqlalchemy.engine.url import make_url


def main() -> int:
    get_settings.cache_clear()
    settings = get_settings()
    parsed = make_url(settings.database_url)
    if parsed.username != "bharathi_user":
        print(f"ERROR: DATABASE_URL user is {parsed.username!r}, expected bharathi_user")
        return 1
    if (parsed.database or "").strip() != "bharathi_erp":
        print("ERROR: DATABASE_URL database is not bharathi_erp")
        return 1
    if parsed.host and str(parsed.port or 5432) != "5432":
        print(f"ERROR: DATABASE_URL port is {parsed.port}, expected 5432")
        return 1
    try:
        with create_engine(settings.database_url).connect() as conn:
            row = conn.execute(
                text("SELECT current_database(), current_user, inet_server_port()")
            ).fetchone()
    except Exception as exc:
        print(f"ERROR: connection failed ({type(exc).__name__})")
        print(
            "Hint: password in DATABASE_URL must match bharathi_user in pgAdmin, "
            "or set DATABASE_PASSWORD in backend/.env"
        )
        return 1
    db, user, port = row
    if db != "bharathi_erp" or user != "bharathi_user":
        print(f"ERROR: connected as {db!r} / {user!r}")
        return 1
    print(f"OK bharathi_erp @ {user} port {port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())