"""List PostgreSQL databases visible to DATABASE_URL user (no secrets printed)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
url = (dotenv_values(ROOT / ".env").get("DATABASE_URL") or "").strip()
if not url:
    sys.exit(2)
admin = url.rsplit("/", 1)[0] + "/postgres"
eng = create_engine(admin)
with eng.connect() as conn:
    for (name,) in conn.execute(
        text("SELECT datname FROM pg_database WHERE datallowconn ORDER BY datname")
    ):
        if name.startswith("bharathi") or "migration" in name:
            print(name)