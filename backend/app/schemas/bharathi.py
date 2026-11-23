from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class BillFileIn(BaseModel):
    stored_file_id: int
    original_filename: str
    mime_type: str
    file_size_bytes: int = 0
    content_sha256: str | None = None


class BillSubmissionCreate(BaseModel):
    vendor_hint: str | None = None
    remarks: str | None = None
    files: list[BillFileIn] = Field(default_factory=list)
    idempotency_key: str | None = None


class BillSubmissionUpdate(BaseModel):
    vendor_hint: str | None = None
    remarks: str | None = None
    status: str | None = None


class BillExtractionOut(BaseModel):
    id: int
    provider: str
    status: str
    extracted: dict[str, Any] | None = None
    confidence: dict[str, Any] | None = None
    error_message: str | None = None


class BillSubmissionOut(BaseModel):
    id: int
    status: str
    vendor_hint: str | None = None
    remarks: str | None = None
    submitted_by_user_id: int
    submitted_at: datetime | None = None
    files: list[dict[str, Any]] = Field(default_factory=list)
    latest_extraction: BillExtractionOut | None = None


class BillVerifyRequest(BaseModel):
    action: str = Field(description="verify | reject | request_correction")
    comment: str | None = None
    corrected_fields: dict[str, Any] | None = None


class CollectionFollowUpIn(BaseModel):
    customer_id: int | None = None
    invoice_ref: str | None = None
    outstanding_amount: float | None = None
    due_date: date | None = None
    next_follow_up_date: date | None = None
    collection_status: str = "open"
    notes: str | None = None


class TallySyncRequest(BaseModel):
    direction: str = Field(description="inbound | outbound")
    dry_run: bool = True


class VendorPriceCompareRow(BaseModel):
    material_key: str
    vendor_name: str
    last_purchase_price: float | None = None
    last_quote_price: float | None = None
    lowest_landed_cost: float | None = None
    currency: str = "INR"
    uom: str | None = None