"""Local development-only demo login (Bharathi ERP UI testing). Never enabled in production."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.core.bharathi_client import BHARATHI_UI_REGISTERABLE_ROLES
from app.core.config import Settings, get_settings
from app.models.user import User
from app.services.auth_service import find_user_by_email, verify_password

# Public identifiers — not secrets; only LOCAL_DEMO_PASSWORD in .env is sensitive.
LOCAL_DEMO_UI_EMAIL_DEFAULT = "demo@bharathi.local"

LOCAL_DEMO_ACCOUNT_EMAIL_BY_ROLE: dict[str, str] = {
    "Admin": "demo-admin@bharathi.local",
    "Accountant": "demo-accountant@bharathi.local",
    "Supervisor": "demo-supervisor@bharathi.local",
    "Store Manager": "demo-storemanager@bharathi.local",
}

LOCAL_DEMO_ACCOUNT_EMAILS = frozenset(LOCAL_DEMO_ACCOUNT_EMAIL_BY_ROLE.values())


@dataclass(frozen=True, slots=True)
class LocalDemoResolveResult:
    kind: Literal["ok", "denied", "skip"]
    user: User | None = None


@dataclass(frozen=True, slots=True)
class LoginIdentity:
    """Email and user to authenticate (after optional local demo resolution)."""

    login_email: str
    user: User | None
    demo_denied: bool = False


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def is_local_demo_login_active(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if settings.is_production:
        return False
    if (settings.environment or "").strip().lower() != "development":
        return False
    if not settings.enable_local_demo_login:
        return False
    if not (settings.local_demo_password or "").strip():
        return False
    base = (settings.frontend_base_url or "").strip().lower()
    if base and not any(token in base for token in ("localhost", "127.0.0.1")):
        return False
    return True


def _is_demo_ui_email(email: str, settings: Settings) -> bool:
    canonical = _norm_email(settings.local_demo_ui_email or LOCAL_DEMO_UI_EMAIL_DEFAULT)
    return _norm_email(email) == canonical


def _normalize_selected_role(role: str | None) -> str | None:
    if not role or not str(role).strip():
        return None
    selected = str(role).strip()
    for name in BHARATHI_UI_REGISTERABLE_ROLES:
        if name.lower() == selected.lower():
            return name
    return None


def try_resolve_local_demo_user(
    db: Session,
    email: str,
    password: str,
    selected_role: str | None,
    *,
    settings: Settings | None = None,
) -> LocalDemoResolveResult:
    """
    Resolve shared demo UI email + role → dedicated demo user.

    Returns skip when not a demo flow (normal login continues).
    Returns denied on failed demo attempt (wrong password / role).
    Returns ok with the target User when credentials match.
    """
    settings = settings or get_settings()
    if not is_local_demo_login_active(settings):
        return LocalDemoResolveResult(kind="skip")

    normalized = _norm_email(email)
    if not _is_demo_ui_email(email, settings):
        if normalized in {_norm_email(e) for e in LOCAL_DEMO_ACCOUNT_EMAILS}:
            return LocalDemoResolveResult(kind="skip")
        return LocalDemoResolveResult(kind="skip")

    role = _normalize_selected_role(selected_role)
    if role not in LOCAL_DEMO_ACCOUNT_EMAIL_BY_ROLE:
        return LocalDemoResolveResult(kind="denied")

    target_email = LOCAL_DEMO_ACCOUNT_EMAIL_BY_ROLE[role]
    user = find_user_by_email(db, target_email)
    if not user or not user.is_active:
        return LocalDemoResolveResult(kind="denied")

    role_names = {r.name for r in (user.roles or [])}
    if role not in role_names:
        return LocalDemoResolveResult(kind="denied")

    if not verify_password(password, user.hashed_password):
        return LocalDemoResolveResult(kind="denied")

    return LocalDemoResolveResult(kind="ok", user=user)


def resolve_login_identity(
    db: Session,
    email: str,
    password: str,
    selected_role: str | None,
    *,
    settings: Settings | None = None,
) -> LoginIdentity:
    """Shared pre-login step for /auth/login and /api/auth/login (operator API)."""
    demo = try_resolve_local_demo_user(
        db, email, password, selected_role, settings=settings
    )
    if demo.kind == "denied":
        return LoginIdentity(login_email=email, user=None, demo_denied=True)
    if demo.kind == "ok" and demo.user is not None:
        return LoginIdentity(
            login_email=demo.user.email,
            user=demo.user,
            demo_denied=False,
        )
    return LoginIdentity(
        login_email=email,
        user=find_user_by_email(db, email),
        demo_denied=False,
    )


def local_demo_login_public_config(settings: Settings | None = None) -> dict[str, str | bool]:
    settings = settings or get_settings()
    return {
        "enabled": is_local_demo_login_active(settings),
        "demo_email": settings.local_demo_ui_email or LOCAL_DEMO_UI_EMAIL_DEFAULT,
        "roles": list(BHARATHI_UI_REGISTERABLE_ROLES),
    }