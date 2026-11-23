#!/usr/bin/env python3
"""Remove Bharathi local demo users only (demo-*@bharathi.local)."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.local_demo_login import LOCAL_DEMO_ACCOUNT_EMAILS
from app.models.user import User


def main() -> int:
    get_settings.cache_clear()
    settings = get_settings()
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT current_database(), current_user")
        ).fetchone()
        if row[0] != "bharathi_erp":
            raise SystemExit(f"Refusing: database is {row[0]!r}, not bharathi_erp")

    from app.core.database import SessionLocal

    db: Session = SessionLocal()
    try:
        removed = 0
        for email in LOCAL_DEMO_ACCOUNT_EMAILS:
            user = db.scalars(select(User).where(User.email == email.lower())).first()
            if user:
                db.delete(user)
                removed += 1
                print(f"Removed {email}")
        db.commit()
        print(f"Done. Removed {removed} demo user(s).")
        print("Set ENABLE_LOCAL_DEMO_LOGIN=false in .env before deployment.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())