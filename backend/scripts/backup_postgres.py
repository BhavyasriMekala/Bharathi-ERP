"""PostgreSQL logical backup via pg_dump (bharathi_erp only).

Usage (from backend/):
  python scripts/backup_postgres.py

Env (optional):
  BACKUP_DIR, KEEP_BACKUPS, PG_DUMP
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine.url import make_url

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_ROOT / ".env"
_ALLOWED_DB = "bharathi_erp"


def _resolve_pg_dump() -> str:
    explicit = (os.getenv("PG_DUMP") or "").strip()
    if explicit:
        return explicit
    for candidate in (
        r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
    ):
        if Path(candidate).is_file():
            return candidate
    return "pg_dump"


def _load_settings_url():
    """Resolve DATABASE_URL the same way as the running app ( .env + DATABASE_PASSWORD )."""
    shell_had_url = bool(os.environ.get("DATABASE_URL", "").strip())
    if _ENV_FILE.is_file():
        load_dotenv(_ENV_FILE, override=True)
    # Import after dotenv so config picks up backend/.env
    if str(_BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(_BACKEND_ROOT))
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    url = (settings.database_url or "").strip()
    if not url.lower().startswith("postgresql"):
        raise ValueError("DATABASE_URL must be postgresql")
    u = make_url(url)
    db_name = (u.database or "").strip()
    if db_name != _ALLOWED_DB:
        raise ValueError(f"Refusing backup: target database must be {_ALLOWED_DB}, not {db_name}")
    source = "backend/.env" if _ENV_FILE.is_file() else "environment"
    if shell_had_url and _ENV_FILE.is_file():
        source = "backend/.env (overrides shell DATABASE_URL if set)"
    return u, source


def _sanitize_pg_message(text: str) -> str:
    if not text:
        return ""
    redacted = re.sub(r"password[=:\s]+\S+", "password=***", text, flags=re.I)
    redacted = re.sub(r"postgresql://[^\s]+", "postgresql://***", redacted, flags=re.I)
    return redacted.strip()[:500]


def _verify_tcp_login(u) -> tuple[bool, str]:
    """Quick login check via psycopg (no secrets in output)."""
    try:
        import psycopg
    except ImportError:
        return True, ""
    try:
        with psycopg.connect(
            host=u.host or "localhost",
            port=u.port or 5432,
            dbname=u.database,
            user=u.username,
            password=u.password or None,
            connect_timeout=8,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database()")
                name = cur.fetchone()[0]
                if name != _ALLOWED_DB:
                    return False, f"connected database mismatch: {name}"
        return True, ""
    except Exception as exc:
        msg = _sanitize_pg_message(str(exc))
        if "password authentication failed" in str(exc).lower():
            return False, (
                "PostgreSQL rejected the credentials from backend/.env "
                "(and DATABASE_PASSWORD if set). Check .env; do not use a stale shell DATABASE_URL."
            )
        return False, msg or type(exc).__name__


def main() -> int:
    try:
        u, source = _load_settings_url()
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"backup_target={_ALLOWED_DB}")
    print(f"credential_source={source}")
    print(f"host={u.host or 'localhost'} port={u.port or 5432} user={u.username or ''}")

    ok, diag = _verify_tcp_login(u)
    if not ok:
        print(f"ERROR: connection verification failed: {diag}")
        return 1

    backup_dir = Path(os.getenv("BACKUP_DIR", str(_BACKEND_ROOT / "backups")))
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = backup_dir / f"bharathi_erp_{stamp}.sql"
    tmp = dest.with_suffix(dest.suffix + ".tmp")

    pg_dump_bin = _resolve_pg_dump()
    env = {k: v for k, v in os.environ.items() if k != "PGPASSWORD"}
    if u.password:
        env["PGPASSWORD"] = u.password

    cmd = [
        pg_dump_bin,
        "--format=plain",
        "--no-owner",
        "--no-acl",
        "-h",
        u.host or "localhost",
        "-p",
        str(u.port or 5432),
        "-U",
        u.username or "",
        "-f",
        str(tmp),
        u.database,
    ]

    try:
        ver = subprocess.run(
            [pg_dump_bin, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if ver.stdout:
            print(ver.stdout.strip())
    except FileNotFoundError:
        print(f"ERROR: pg_dump not found at {pg_dump_bin}")
        return 1

    try:
        proc = subprocess.run(cmd, check=False, env=env, capture_output=True, text=True)
    except FileNotFoundError:
        print(f"ERROR: pg_dump not found at {pg_dump_bin}")
        return 1

    if proc.returncode != 0:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        hint = _sanitize_pg_message(proc.stderr or proc.stdout or "")
        print(f"ERROR: pg_dump exit code {proc.returncode}")
        if "password authentication failed" in (proc.stderr or "").lower():
            print(
                "HINT: Authentication failed. Ensure backend/.env DATABASE_URL and "
                "optional DATABASE_PASSWORD match the PostgreSQL role (pg_dump uses PGPASSWORD, not URL on CLI)."
            )
        elif hint:
            print(f"detail: {hint}")
        return proc.returncode or 1

    if not tmp.is_file() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        print("ERROR: backup file missing or empty after pg_dump")
        return 1

    tmp.replace(dest)
    size = dest.stat().st_size
    print(f"Backup written: {dest}")
    print(f"backup_bytes={size}")
    print("status=success")

    keep = int(os.getenv("KEEP_BACKUPS", "14"))
    existing = sorted(
        backup_dir.glob("bharathi_erp_*.sql"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for stale in existing[keep:]:
        stale.unlink(missing_ok=True)
        print(f"Pruned old backup: {stale.name}")

    # Retain legacy pattern prune
    for stale in sorted(backup_dir.glob("insights_iva_*.sql"), key=lambda p: p.stat().st_mtime, reverse=True)[
        keep:
    ]:
        stale.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())