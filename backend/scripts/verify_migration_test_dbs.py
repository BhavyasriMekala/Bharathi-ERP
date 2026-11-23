from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
url = dotenv_values(ROOT / ".env")["DATABASE_URL"]
base = url.rsplit("/", 1)[0]
eng0 = create_engine(url)
with eng0.connect() as c:
    rows = c.execute(
        text(
            "SELECT datname, pg_catalog.pg_get_userbyid(datdba) AS owner "
            "FROM pg_catalog.pg_database WHERE datname LIKE 'bharathi%' ORDER BY 1"
        )
    ).fetchall()
    print("catalog:", [f"{r[0]}({r[1]})" for r in rows])

for db in ("bharathi_migration_test", "bharathi_migration_test_fresh", "bharathi_erp"):
    eng = create_engine(f"{base}/{db}")
    try:
        with eng.connect() as c:
            name = c.execute(text("SELECT current_database()")).scalar()
            owner = c.execute(
                text(
                    "SELECT pg_catalog.pg_get_userbyid(d.datdba) FROM pg_catalog.pg_database d WHERE d.datname = current_database()"
                )
            ).scalar()
            print(f"{db}: reachable name={name} owner={owner}")
    except Exception as exc:
        print(f"{db}: UNREACHABLE {type(exc).__name__}")