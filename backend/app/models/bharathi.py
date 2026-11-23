"""Bharathi-specific persistence: bill capture, OCR, collections, Tally sync."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BharathiBillSubmission(Base, TimestampMixin):
    __tablename__ = "bharathi_bill_submissions"
    __table_args__ = (
        Index("ix_bharathi_bill_submissions_tenant_status", "tenant_id", "status"),
        Index("ix_bharathi_bill_submissions_submitter", "tenant_id", "submitted_by_user_id"),
        Index("ix_bharathi_bill_business_key", "tenant_id", "supplier_identity_key", "invoice_number_norm"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    submitted_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    vendor_hint: Mapped[str | None] = mapped_column(String(255))
    remarks: Mapped[str | None] = mapped_column(Text)
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("bharathi_bill_submissions.id"))
    duplicate_status: Mapped[str | None] = mapped_column(String(32))
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supplier_name: Mapped[str | None] = mapped_column(String(255))
    supplier_gstin: Mapped[str | None] = mapped_column(String(20))
    supplier_identity_key: Mapped[str | None] = mapped_column(String(128))
    invoice_number: Mapped[str | None] = mapped_column(String(128))
    invoice_number_norm: Mapped[str | None] = mapped_column(String(128))
    invoice_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    currency_code: Mapped[str | None] = mapped_column(String(8))
    grand_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    validation_warnings_json: Mapped[str | None] = mapped_column(Text)
    verified_fields_json: Mapped[str | None] = mapped_column(Text)
    verified_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tally_sync_status: Mapped[str | None] = mapped_column(String(32), default="not_configured")


class BharathiBillFile(Base, TimestampMixin):
    __tablename__ = "bharathi_bill_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("bharathi_bill_submissions.id", ondelete="CASCADE"), nullable=False
    )
    stored_file_id: Mapped[int | None] = mapped_column(ForeignKey("stored_files.id"))
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(nullable=False, default=0)
    content_sha256: Mapped[str | None] = mapped_column(String(64))


class BharathiPurchaseInvoiceLine(Base, TimestampMixin):
    __tablename__ = "bharathi_purchase_invoice_lines"
    __table_args__ = (
        Index("ix_bharathi_inv_lines_submission", "tenant_id", "submission_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("bharathi_bill_submissions.id", ondelete="CASCADE"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(nullable=False, default=1)
    description: Mapped[str | None] = mapped_column(String(512))
    hsn_sac: Mapped[str | None] = mapped_column(String(32))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    unit: Mapped[str | None] = mapped_column(String(32))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    taxable_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    line_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))


class BharathiBillOcrJob(Base, TimestampMixin):
    __tablename__ = "bharathi_bill_ocr_jobs"
    __table_args__ = (
        Index("ix_bharathi_ocr_jobs_submission", "tenant_id", "submission_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("bharathi_bill_submissions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    provider: Mapped[str | None] = mapped_column(String(64))
    model_name: Mapped[str | None] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(nullable=False, default=3)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BharathiBillExtraction(Base, TimestampMixin):
    __tablename__ = "bharathi_bill_extractions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("bharathi_bill_submissions.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="mock")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    extracted_json: Mapped[str | None] = mapped_column(Text)
    confidence_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)


class BharathiBillVerificationEvent(Base):
    __tablename__ = "bharathi_bill_verification_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("bharathi_bill_submissions.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BharathiCollectionFollowUp(Base, TimestampMixin):
    __tablename__ = "bharathi_collection_followups"
    __table_args__ = (
        Index("ix_bharathi_followups_tenant_customer", "tenant_id", "customer_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    customer_id: Mapped[int | None] = mapped_column()
    invoice_ref: Mapped[str | None] = mapped_column(String(128))
    outstanding_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    due_date: Mapped[date | None] = mapped_column(Date)
    follow_up_owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    next_follow_up_date: Mapped[date | None] = mapped_column(Date)
    collection_status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class BharathiTallyMapping(Base, TimestampMixin):
    __tablename__ = "bharathi_tally_mappings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_type", "erp_key", name="uq_bharathi_tally_map"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    erp_key: Mapped[str] = mapped_column(String(255), nullable=False)
    tally_guid: Mapped[str | None] = mapped_column(String(128))
    tally_name: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[str | None] = mapped_column(Text)


class BharathiTallySyncRun(Base, TimestampMixin):
    __tablename__ = "bharathi_tally_sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cursor_before: Mapped[str | None] = mapped_column(Text)
    cursor_after: Mapped[str | None] = mapped_column(Text)
    stats_json: Mapped[str | None] = mapped_column(Text)


class BharathiTallySyncItem(Base, TimestampMixin):
    __tablename__ = "bharathi_tally_sync_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    run_id: Mapped[int] = mapped_column(ForeignKey("bharathi_tally_sync_runs.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    payload_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    tally_voucher_key: Mapped[str | None] = mapped_column(String(255))