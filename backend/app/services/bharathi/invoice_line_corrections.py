"""Persist accountant corrections to invoice headers and lines without mutating OCR source."""

from __future__ import annotations

import json
from datetime import date

from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.bharathi import BharathiBillSubmission, BharathiPurchaseInvoiceLine
from app.services.bharathi.duplicate_detection import norm_invoice_number, supplier_identity_key
from app.services.bharathi.invoice_extraction_schema import InvoiceLineItem, parse_extraction_payload
from app.services.bharathi.invoice_validation import validate_extraction


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def validate_corrected_line_items(rows: list[dict] | None) -> list[InvoiceLineItem]:
    if not rows:
        return []
    out: list[InvoiceLineItem] = []
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise HTTPException(400, f"Line {idx} must be an object")
        out.append(InvoiceLineItem.model_validate(row))
    return out


def apply_header_corrections(sub: BharathiBillSubmission, corrected: dict) -> list[dict]:
    """Apply header fields from corrected_fields; returns validation warnings."""
    if not corrected:
        return []
    merged = parse_extraction_payload(
        {
            "supplier_name": corrected.get("supplier_name", sub.supplier_name),
            "supplier_gstin": corrected.get("supplier_gstin", sub.supplier_gstin),
            "invoice_number": corrected.get("invoice_number", sub.invoice_number),
            "invoice_date": corrected.get("invoice_date", sub.invoice_date.isoformat() if sub.invoice_date else None),
            "due_date": corrected.get("due_date"),
            "grand_total": corrected.get("grand_total", sub.grand_total),
            "currency": corrected.get("currency_code", sub.currency_code),
            "line_items": [],
        }
    )
    warnings = validate_extraction(merged)
    if "supplier_name" in corrected:
        sub.supplier_name = merged.supplier_name
    if "supplier_gstin" in corrected:
        sub.supplier_gstin = merged.supplier_gstin
    if "invoice_number" in corrected:
        sub.invoice_number = merged.invoice_number
        sub.invoice_number_norm = norm_invoice_number(merged.invoice_number)
    if "invoice_date" in corrected:
        sub.invoice_date = _parse_date(merged.invoice_date)
    if "grand_total" in corrected:
        sub.grand_total = merged.grand_total
    if "currency_code" in corrected:
        sub.currency_code = (merged.currency or "INR")[:8]
    sub.supplier_identity_key = supplier_identity_key(
        gstin=sub.supplier_gstin,
        supplier_name=sub.supplier_name,
        vendor_hint=sub.vendor_hint,
    )
    sub.validation_warnings_json = json.dumps(warnings)
    return warnings


def persist_corrected_line_items(db: Session, sub: BharathiBillSubmission, rows: list[InvoiceLineItem]) -> None:
    if not rows:
        return
    db.execute(delete(BharathiPurchaseInvoiceLine).where(BharathiPurchaseInvoiceLine.submission_id == sub.id))
    for idx, line in enumerate(rows, start=1):
        line_num = idx
        db.add(
            BharathiPurchaseInvoiceLine(
                tenant_id=sub.tenant_id,
                submission_id=sub.id,
                line_number=line_num,
                description=line.description,
                hsn_sac=line.hsn_sac,
                quantity=line.quantity,
                unit=line.unit,
                unit_price=line.unit_price,
                discount_amount=line.discount_amount,
                tax_rate=line.tax_rate,
                taxable_amount=line.taxable_amount,
                tax_amount=line.tax_amount,
                line_total=line.line_total,
            )
        )