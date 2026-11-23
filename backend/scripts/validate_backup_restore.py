"""Safe backup restore validation — disposable DB only. Never touches bharathi_erp data."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine.url import make_url

ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "backups" / "bharathi_erp_20261123T134923Z.sql"
RESTORE_DB = "bharathi_backup_restore_test_20261123"
PROTECTED = frozenset(
    {
        "bharathi_erp",
        "insights_iva",
        "smrt_db",
        "postgres",
        "bharathi_migration_test",
        "bharathi_migration_test_fresh",
    }
)

FORBIDDEN_DUMP_PATTERNS = [
    re.compile(r"^\s*CREATE\s+DATABASE\b", re.I | re.M),
    re.compile(r"^\s*DROP\s+DATABASE\b", re.I | re.M),
    re.compile(r"^\\connect\b", re.I | re.M),
    re.compile(r"^\\c\s+", re.I | re.M),
]


def _settings_url():
    load_dotenv(ROOT / ".env", override=True)
    sys.path.insert(0, str(ROOT))
    from app.core.config import get_settings

    get_settings.cache_clear()
    u = make_url(get_settings().database_url)
    if (u.database or "") != "bharathi_erp":
        raise SystemExit(f"ERROR: DATABASE_URL must point at bharathi_erp, not {u.database}")
    return u


def _connect(dbname: str, u, *, user: str | None = None, password: str | None = None):
    import psycopg

    return psycopg.connect(
        host=u.host or "localhost",
        port=u.port or 5432,
        dbname=dbname,
        user=user or u.username,
        password=password if password is not None else (u.password or None),
        connect_timeout=20,
    )


def _parse_pg_admin_url() -> tuple[str, str, str, int] | None:
    raw = (os.getenv("PG_ADMIN_URL") or "").strip()
    if not raw:
        return None
    from urllib.parse import unquote, urlparse

    parsed = urlparse(raw.replace("+psycopg", "", 1).replace("postgresql://", "postgresql://", 1))
    if not parsed.hostname:
        return None
    return (
        parsed.hostname,
        parsed.username or "postgres",
        unquote(parsed.password or ""),
        parsed.port or 5432,
    )


def _admin_create_db(u) -> tuple[bool, str]:
    """Create RESTORE_DB using superuser (POSTGRES_ADMIN_* or localhost postgres heuristic)."""
    import psycopg
    from psycopg import sql

    host = u.host or "localhost"
    if host not in {"127.0.0.1", "localhost"}:
        return False, "refused_remote_host"

    admin_user = (os.getenv("POSTGRES_ADMIN_USER") or "postgres").strip()
    admin_password = (os.getenv("POSTGRES_ADMIN_PASSWORD") or "").strip()
    candidates: list[tuple[str, str, str, int]] = []
    pg_admin = _parse_pg_admin_url()
    if pg_admin:
        candidates.append(pg_admin)
    if admin_password:
        candidates.append((host, admin_user, admin_password, u.port or 5432))
    if u.password:
        candidates.append((host, "postgres", u.password, u.port or 5432))

    last_err = ""
    seen: set[tuple[str, str]] = set()
    for chost, user, pwd, port in candidates:
        key = (user, chost)
        if key in seen:
            continue
        seen.add(key)
        try:
            with psycopg.connect(
                host=chost,
                port=port,
                dbname="postgres",
                user=user,
                password=pwd or None,
                connect_timeout=15,
                autocommit=True,
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        sql.SQL(
                            "CREATE DATABASE {} WITH OWNER = {} ENCODING 'UTF8' TEMPLATE template0"
                        ).format(sql.Identifier(RESTORE_DB), sql.Identifier("bharathi_user"))
                    )
            return True, f"created_by={user}"
        except Exception as exc:
            last_err = type(exc).__name__
            continue
    return False, last_err or "no_admin_credentials"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_psql() -> str:
    explicit = (os.getenv("PSQL") or "").strip()
    if explicit:
        return explicit
    for candidate in (
        r"C:\Program Files\PostgreSQL\18\bin\psql.exe",
        r"C:\Program Files\PostgreSQL\17\bin\psql.exe",
    ):
        if Path(candidate).is_file():
            return candidate
    return "psql"


def _pg_env(password: str | None) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "PGPASSWORD"}
    if password:
        env["PGPASSWORD"] = password
    return env


def _scalar(conn, sql: str, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        row = cur.fetchone()
        return row[0] if row else None


def main() -> int:
    report: dict[str, str] = {}

    if not BACKUP.is_file():
        print("RESTORE_TEST=FAIL")
        print("detail=backup missing")
        return 1

    size = BACKUP.stat().st_size
    if size <= 0:
        print("RESTORE_TEST=FAIL")
        print("detail=backup empty")
        return 1

    digest = _sha256(BACKUP)
    report["BACKUP_FILE"] = str(BACKUP)
    report["BACKUP_SIZE"] = str(size)
    report["BACKUP_SHA256"] = digest

    head = BACKUP.read_text(encoding="utf-8", errors="replace")[:500_000]
    for pat in FORBIDDEN_DUMP_PATTERNS:
        if pat.search(head):
            print("RESTORE_TEST=FAIL")
            print("detail=backup contains forbidden database-switch or CREATE/DROP DATABASE")
            return 1
    if "PostgreSQL database dump" not in head[:2000] or "alembic_version" not in head:
        print("RESTORE_TEST=FAIL")
        print("detail=backup does not look like a valid ERP plain SQL dump")
        return 1
    if "Dumped by pg_dump version 18" not in head[:500]:
        report["PG_DUMP_HEADER"] = "check_manually"
    else:
        report["PG_DUMP_HEADER"] = "18.x"

    u = _settings_url()
    try:
        with _connect("bharathi_erp", u) as conn:
            src_rev_before = _scalar(conn, "SELECT version_num FROM alembic_version")
    except Exception as exc:
        print("RESTORE_TEST=FAIL")
        print("detail=cannot verify source bharathi_erp (credentials)")
        print(f"error_type={type(exc).__name__}")
        return 1

    with _connect("postgres", u) as conn:
        conn.autocommit = True
        exists = _scalar(conn, "SELECT 1 FROM pg_database WHERE datname = %s", (RESTORE_DB,))
        if exists:
            print("RESTORE_TEST=FAIL")
            print(f"detail=restore database {RESTORE_DB} already exists — STOP (no overwrite)")
            return 1
        protected = []
        with conn.cursor() as cur:
            cur.execute(
                "SELECT datname FROM pg_database WHERE datname = ANY(%s) ORDER BY 1",
                (list(PROTECTED),),
            )
            protected = [r[0] for r in cur.fetchall()]
        report["PROTECTED_DATABASE_SAFETY_CHECK"] = "present:" + ",".join(protected)

        try:
            with conn.cursor() as cur:
                cur.execute(
                    f'CREATE DATABASE "{RESTORE_DB}" '
                    f"WITH OWNER = bharathi_user ENCODING 'UTF8' TEMPLATE template0"
                )
            report["RESTORE_DB_CREATE"] = "bharathi_user"
        except Exception:
            ok, detail = _admin_create_db(u)
            if not ok:
                report["SOURCE_DATABASE"] = "bharathi_erp"
                report["RESTORE_DATABASE"] = RESTORE_DB
                report["SOURCE_ALEMBIC_REVISION"] = str(src_rev_before)
                report["BACKUP_INTEGRITY_CHECK"] = "PASS"
                report["SCHEMA_CHECK"] = "SKIPPED"
                report["ROW_COUNT_CHECK"] = "SKIPPED"
                report["RESTORE_EXIT_CODE"] = "SKIPPED"
                report["RESTORED_TABLE_COUNT"] = "SKIPPED"
                report["RESTORED_ALEMBIC_REVISION"] = "SKIPPED"
                report["RESTORE_DATABASE_OWNER"] = "SKIPPED"
                report["PROTECTED_DATABASE_SAFETY_CHECK"] = report.get(
                    "PROTECTED_DATABASE_SAFETY_CHECK", "SKIPPED"
                )
                report["RESTORE_TEST"] = "FAIL"
                for k in (
                    "BACKUP_FILE",
                    "BACKUP_SIZE",
                    "BACKUP_SHA256",
                    "PG_VERSION",
                    "SOURCE_DATABASE",
                    "RESTORE_DATABASE",
                    "SOURCE_ALEMBIC_REVISION",
                ):
                    if k in report:
                        print(f"{k}={report[k]}")
                print("RESTORE_TEST=FAIL")
                print("detail=could not create restore database (need superuser)")
                print(
                    "pgAdmin: Register Server, Create Database: "
                    f"Name={RESTORE_DB}, Owner=bharathi_user, Encoding=UTF8, Template=template0"
                )
                print(
                    "Or set POSTGRES_ADMIN_PASSWORD (or PG_ADMIN_URL), then re-run validate_backup_restore.py"
                )
                print(f"create_error={detail}")
                return 1
            report["RESTORE_DB_CREATE"] = detail

    psql = _resolve_psql()
    ver = subprocess.run([psql, "--version"], capture_output=True, text=True)
    report["PG_VERSION"] = (ver.stdout or ver.stderr or "").strip().split("\n")[0]

    env = _pg_env(u.password)
    cmd = [
        psql,
        "-X",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        u.host or "localhost",
        "-p",
        str(u.port or 5432),
        "-U",
        u.username or "",
        "-d",
        RESTORE_DB,
        "-f",
        str(BACKUP),
    ]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    report["RESTORE_EXIT_CODE"] = str(proc.returncode)
    report["SOURCE_DATABASE"] = "bharathi_erp"
    report["RESTORE_DATABASE"] = RESTORE_DB

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[:300]
        err = re.sub(r"password=\S+", "password=***", err, flags=re.I)
        print("RESTORE_TEST=FAIL")
        for k, v in report.items():
            print(f"{k}={v}")
        print(f"psql_detail={err}")
        return proc.returncode or 1

    report["BACKUP_INTEGRITY_CHECK"] = "PASS" if _sha256(BACKUP) == digest else "FAIL"

    with _connect(RESTORE_DB, u) as rconn, _connect("bharathi_erp", u) as sconn:
        name = _scalar(rconn, "SELECT current_database()")
        owner = _scalar(
            rconn,
            "SELECT pg_catalog.pg_get_userbyid(d.datdba) FROM pg_database d WHERE d.datname = current_database()",
        )
        report["RESTORE_DATABASE_OWNER"] = str(owner)
        if name != RESTORE_DB:
            report["RESTORE_TEST"] = "FAIL"
            print("RESTORE_TEST=FAIL")
            return 1

        tbl = _scalar(
            rconn,
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE'",
        )
        report["RESTORED_TABLE_COUNT"] = str(tbl)

        src_rev = _scalar(sconn, "SELECT version_num FROM alembic_version")
        res_rev = _scalar(rconn, "SELECT version_num FROM alembic_version")
        report["SOURCE_ALEMBIC_REVISION"] = str(src_rev)
        report["RESTORED_ALEMBIC_REVISION"] = str(res_rev)

        schema_ok = []
        if res_rev != "b0a1r2a3t4h5i":
            schema_ok.append("alembic_revision_mismatch")
        if not _scalar(rconn, "SELECT to_regclass('public.bharathi_bill_submissions')"):
            schema_ok.append("missing_bharathi_bill_submissions")
        child_lines = bool(_scalar(rconn, "SELECT to_regclass('public.bharathi_purchase_invoice_lines')"))
        child_ocr = bool(_scalar(rconn, "SELECT to_regclass('public.bharathi_bill_ocr_jobs')"))
        report["PHASE1_CHILD_TABLES"] = f"lines={child_lines},ocr_jobs={child_ocr}"
        report["SCHEMA_CHECK"] = "PASS" if not schema_ok else "FAIL:" + ",".join(schema_ok)

        row_mism = []
        for table in ("tenants", "users", "bharathi_bill_submissions"):
            if not _scalar(
                rconn,
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name=%s)",
                (table,),
            ):
                continue
            sc = _scalar(sconn, f"SELECT COUNT(*) FROM {table}")
            rc = _scalar(rconn, f"SELECT COUNT(*) FROM {table}")
            if sc != rc:
                row_mism.append(f"{table}:{sc}!={rc}")
        report["ROW_COUNT_CHECK"] = "PASS" if not row_mism else "FAIL:" + ";".join(row_mism)

        src_rev_after = _scalar(sconn, "SELECT version_num FROM alembic_version")
        if src_rev_after != src_rev_before:
            report["PROTECTED_DATABASE_SAFETY_CHECK"] += ";bharathi_erp_revision_changed"
        elif src_rev_after != "b0a1r2a3t4h5i":
            report["PROTECTED_DATABASE_SAFETY_CHECK"] += f";bharathi_erp_rev={src_rev_after}"
        else:
            report["PROTECTED_DATABASE_SAFETY_CHECK"] += ";bharathi_erp_unchanged"

    ok = (
        report.get("BACKUP_INTEGRITY_CHECK") == "PASS"
        and report.get("SCHEMA_CHECK") == "PASS"
        and report.get("ROW_COUNT_CHECK") == "PASS"
        and report.get("RESTORED_ALEMBIC_REVISION") == "b0a1r2a3t4h5i"
        and proc.returncode == 0
        and "bharathi_erp_revision_changed" not in report.get("PROTECTED_DATABASE_SAFETY_CHECK", "")
    )
    report["RESTORE_TEST"] = "PASS" if ok else "FAIL"

    for k in (
        "BACKUP_FILE",
        "BACKUP_SIZE",
        "BACKUP_SHA256",
        "PG_VERSION",
        "SOURCE_DATABASE",
        "RESTORE_DATABASE",
        "RESTORE_DATABASE_OWNER",
        "RESTORE_EXIT_CODE",
        "RESTORED_TABLE_COUNT",
        "SOURCE_ALEMBIC_REVISION",
        "RESTORED_ALEMBIC_REVISION",
        "PHASE1_CHILD_TABLES",
        "SCHEMA_CHECK",
        "ROW_COUNT_CHECK",
        "BACKUP_INTEGRITY_CHECK",
        "PROTECTED_DATABASE_SAFETY_CHECK",
        "RESTORE_TEST",
    ):
        print(f"{k}={report.get(k, 'SKIPPED')}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())