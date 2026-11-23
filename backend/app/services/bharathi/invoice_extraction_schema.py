"""Structured purchase invoice extraction schema (no fabricated fields)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, field_validator


class InvoiceLineItem(BaseModel):
    description: str | None = None
    hsn_sac: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    discount_amount: Decimal | None = None
    tax_rate: Decimal | None = None
    taxable_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    line_total: Decimal | None = None


class InvoiceExtraction(BaseModel):
    supplier_name: str | None = None
    supplier_gstin: str | None = None
    supplier_address: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    purchase_order_reference: str | None = None
    currency: str | None = "INR"
    subtotal: Decimal | None = None
    discount: Decimal | None = None
    freight_other_charges: Decimal | None = None
    cgst: Decimal | None = None
    sgst: Decimal | None = None
    igst: Decimal | None = None
    round_off: Decimal | None = None
    grand_total: Decimal | None = None
    payment_terms: str | None = None
    line_items: list[InvoiceLineItem] = Field(default_factory=list)

    @field_validator(
        "subtotal",
        "discount",
        "freight_other_charges",
        "cgst",
        "sgst",
        "igst",
        "round_off",
        "grand_total",
        mode="before",
    )
    @classmethod
    def _decimal_fields(cls, v: Any) -> Decimal | None:
        if v is None or v == "":
            return None
        try:
            return Decimal(str(v))
        except (InvalidOperation, ValueError, TypeError):
            return None


def parse_extraction_payload(data: dict[str, Any]) -> InvoiceExtraction:
    lines = data.get("line_items") or []
    parsed_lines = []
    for row in lines:
        if not isinstance(row, dict):
            continue
        parsed_lines.append(InvoiceLineItem.model_validate(row))
    payload = {**data, "line_items": parsed_lines}
    return InvoiceExtraction.model_validate(payload)


def extraction_to_db_dict(ext: InvoiceExtraction) -> dict[str, Any]:
    return ext.model_dump(mode="json")