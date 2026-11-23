"""Bharathi Enterprises client profile — feature visibility, UI roles, defaults.

Legacy manufacturing roles remain in the database and PERMISSION_MATRIX for
compatibility; user-management UIs filter to BHARATHI_UI_REGISTERABLE_ROLES.
"""

from __future__ import annotations

import json
from typing import Any

CLIENT_LEGAL_NAME = "Bharathi Enterprises"
CLIENT_DISPLAY_NAME = "Bharathi Enterprises ERP"
CLIENT_INDUSTRY = (
    "Manufacturing and supply of electrical line materials, air break switches, "
    "HG fuse sets, cross arms, stay sets, meter boxes, and related products."
)

# Placeholders — replace via Company Settings / Admin UI after verification.
CLIENT_PROFILE_DEFAULTS: dict[str, Any] = {
    "company_name": CLIENT_LEGAL_NAME,
    "legal_name": CLIENT_LEGAL_NAME,
    "country": "India",
    "currency_code": "INR",
    "financial_year_start_month": 4,
    "date_format": "DD/MM/YYYY",
    "amount_format_locale": "en-IN",
    "default_gst_pct": 18.0,
    "industry_description": CLIENT_INDUSTRY,
}

BHARATHI_UI_REGISTERABLE_ROLES = ("Admin", "Accountant", "Supervisor", "Store Manager")

# Sidebar module keys hidden for Bharathi (backend routes remain for shared code).
BHARATHI_HIDDEN_MODULES = frozenset({
    "production",
    "factoryMonitor",
    "iot",
    "hr",
    "quality",
    "maintenance",
    "chat",
    "meetings",
    "analytics",
})

BHARATHI_PRIORITY_MODULES = frozenset({
    "dashboard",
    "bharathi_bills",
    "bharathi_tally",
    "bharathi_collections",
    "accounts",
    "sales",
    "procurement",
    "masters",
    "inventory",
    "documents",
    "alerts",
    "reports",
    "settings",
    "admin",
})

BILL_SUBMISSION_STATUSES = (
    "DRAFT",
    "SUBMITTED",
    "OCR_PROCESSING",
    "EXTRACTED",
    "EXTRACTION_FAILED",
    "NEEDS_REVIEW",
    "DUPLICATE_REVIEW",
    "PENDING_VERIFICATION",
    "VERIFIED",
    "APPROVED",
    "REJECTED",
    "POSTED",
    "SYNC_PENDING",
    "SYNCED",
    "SYNC_FAILED",
)


def bharathi_custom_fields_json() -> str:
    return json.dumps(
        {
            "client_pack": "bharathi_enterprises",
            "currency": "INR",
            "locale": "en-IN",
        }
    )