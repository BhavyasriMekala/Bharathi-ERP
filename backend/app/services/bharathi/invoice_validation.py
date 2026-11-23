"""Validation warnings for extracted / corrected invoice fields."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from app.services.bharathi.invoice_extraction_schema import InvoiceExtraction

_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$", re.I)
_AMOUNT_TOLERANCE = Decimal("2.00")


def validate_gstin(gstin: str | None) -> list[str]:
    if not gstin or not str(gstin).strip():
        return []
    if not _GSTIN_RE.match(str(gstin).strip().upper()):
        return ["invalid_gstin_format"]
    return []


def validate_extraction(ext: InvoiceExtraction) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    if not (ext.supplier_name or "").strip():
        warnings.append({"code": "missing_supplier", "field": "supplier_name"})
    if not (ext.invoice_number or "").strip():
        warnings.append({"code": "missing_invoice_number", "field": "invoice_number"})
    if not ext.invoice_date:
        warnings.append({"code": "missing_invoice_date", "field": "invoice_date"})
    if ext.grand_total is None:
        warnings.append({"code": "missing_grand_total", "field": "grand_total"})
    for code in validate_gstin(ext.supplier_gstin):
        warnings.append({"code": code, "field": "supplier_gstin"})
    if ext.line_items:
        line_sum = Decimal("0")
        for li in ext.line_items:
            if li.quantity is not None and li.quantity < 0:
                warnings.append({"code": "negative_quantity", "field": "line_items"})
            if li.line_total is not None:
                line_sum += li.line_total
        if ext.grand_total is not None and line_sum > 0:
            diff = abs(line_sum - ext.grand_total)
            if diff > _AMOUNT_TOLERANCE:
                warnings.append({"code": "line_total_mismatch", "field": "grand_total"})
    return warnings


def warnings_need_review(warnings: list[dict[str, str]]) -> bool:
    critical = {"missing_supplier", "missing_invoice_number", "missing_invoice_date", "missing_grand_total"}
    return any(w.get("code") in critical for w in warnings)