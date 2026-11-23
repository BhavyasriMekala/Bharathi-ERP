"""Apply Bharathi default company profile (idempotent, placeholders only)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.bharathi_client import CLIENT_PROFILE_DEFAULTS, bharathi_custom_fields_json
from app.models.company_settings import CompanySettings


def ensure_bharathi_company_profile(db: Session, tenant_id: int) -> CompanySettings:
    row = db.scalar(select(CompanySettings).where(CompanySettings.tenant_id == tenant_id))
    if row is None:
        row = CompanySettings(tenant_id=tenant_id)
        db.add(row)
    if not (row.company_name or "").strip():
        row.company_name = CLIENT_PROFILE_DEFAULTS["company_name"]
    if not (row.legal_name or "").strip():
        row.legal_name = CLIENT_PROFILE_DEFAULTS["legal_name"]
    if not (row.country or "").strip():
        row.country = CLIENT_PROFILE_DEFAULTS["country"]
    if row.default_gst_pct is None:
        row.default_gst_pct = CLIENT_PROFILE_DEFAULTS["default_gst_pct"]
    if not (row.custom_fields_json or "").strip():
        row.custom_fields_json = bharathi_custom_fields_json()
    db.commit()
    db.refresh(row)
    return row