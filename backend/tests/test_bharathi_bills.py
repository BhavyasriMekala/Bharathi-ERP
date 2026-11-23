"""Bharathi bill workflow and RBAC tests."""

import json

import pytest

from app.core.rbac_constants import PERMISSION_MATRIX
from app.services.bharathi.ocr_providers import MockOcrProvider
from app.services.bharathi.vendor_pricing_service import compare_vendor_rows


def test_supervisor_role_in_matrix():
    assert "Supervisor" in PERMISSION_MATRIX
    mods = PERMISSION_MATRIX["Supervisor"]["modules"]
    assert "bharathi_bills" in mods
    assert "accounts" not in mods


def test_accountant_has_bill_and_tally_modules():
    mods = PERMISSION_MATRIX["Accountant"]["modules"]
    assert "bharathi_bills" in mods
    assert "bharathi_tally" in mods


def test_mock_ocr_returns_structured_invoice():
    data, conf = MockOcrProvider().extract_invoice(filename="a.jpg", mime_type="image/jpeg", hints={})
    assert data["invoice_total"] > 0
    assert conf["invoice_number"] >= 0.5


def test_vendor_price_compare_normalizes_uom():
    rows = [
        {"material_key": "HG Fuse", "vendor_name": "V1", "unit_price": 100, "quantity": 10, "gst_pct": 18, "uom": "pcs"},
        {"material_key": "HG Fuse", "vendor_name": "V2", "unit_price": 95, "quantity": 10, "gst_pct": 18, "uom": "ea", "freight": 50},
    ]
    out = compare_vendor_rows(rows)
    assert len(out) == 1
    assert out[0]["suggested_vendor"] in ("V1", "V2")