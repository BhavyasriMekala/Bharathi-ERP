"""Try to create approved disposable DBs (no CREATEDB grant to bharathi_user)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
NAMES = ("bharathi_migration_test", "bharathi_migration_test_fresh")


def main() -> int:
    url = (dotenv_values(ROOT / ".env").get("DATABASE_URL") or "").strip()
    if not url:
        print("DATABASE_URL missing")
        return 2
    admin = url.rsplit("/", 1)[0] + "/postgres"
    eng = create_engine(admin, isolation_level="AUTOCOMMIT")
    rc = 0
    with eng.connect() as conn:
        for name in NAMES:
            exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname=:n"), {"n": name}).scalar()
            if exists:
                print(f"{name}=EXISTS")
                continue
            try:
                conn.execute(text(f'CREATE DATABASE "{name}"'))
                print(f"{name}=CREATED")
            except Exception as exc:
                print(f"{name}=CREATE_FAILED {type(exc).__name__}")
                rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())