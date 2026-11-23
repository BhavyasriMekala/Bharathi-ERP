"""Phase 1 Bharathi purchase invoice lines, header fields, OCR jobs.

Revision ID: b1p1h2a3s4e5
Revises: b0a1r2a3t4h5i
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1p1h2a3s4e5"
down_revision: Union[str, Sequence[str], None] = "b0a1r2a3t4h5i"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ACTIVE_DUPLICATE_STATUSES = (
    "DRAFT",
    "SUBMITTED",
    "OCR_PROCESSING",
    "EXTRACTED",
    "NEEDS_REVIEW",
    "PENDING_VERIFICATION",
    "VERIFIED",
    "APPROVED",
    "DUPLICATE_REVIEW",
    "SYNC_PENDING",
)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("bharathi_bill_submissions"):
        cols = {c["name"] for c in insp.get_columns("bharathi_bill_submissions")}
        additions = [
            ("supplier_name", sa.String(255)),
            ("supplier_gstin", sa.String(20)),
            ("supplier_identity_key", sa.String(128)),
            ("invoice_number", sa.String(128)),
            ("invoice_number_norm", sa.String(128)),
            ("invoice_date", sa.Date()),
            ("due_date", sa.Date()),
            ("currency_code", sa.String(8)),
            ("grand_total", sa.Numeric(18, 2)),
            ("duplicate_status", sa.String(32)),
            ("validation_warnings_json", sa.Text()),
            ("verified_fields_json", sa.Text()),
            ("approved_by_user_id", sa.Integer()),
            ("approved_at", sa.DateTime(timezone=True)),
            ("rejected_by_user_id", sa.Integer()),
            ("rejected_at", sa.DateTime(timezone=True)),
            ("tally_sync_status", sa.String(32)),
        ]
        for name, coltype in additions:
            if name not in cols:
                op.add_column("bharathi_bill_submissions", sa.Column(name, coltype, nullable=True))
        fk_cols = {c["name"] for c in insp.get_columns("bharathi_bill_submissions")}
        if "approved_by_user_id" in fk_cols:
            pass  # FK optional on SQLite dev

    if not insp.has_table("bharathi_purchase_invoice_lines"):
        op.create_table(
            "bharathi_purchase_invoice_lines",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("submission_id", sa.Integer(), nullable=False),
            sa.Column("line_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("description", sa.String(length=512), nullable=True),
            sa.Column("hsn_sac", sa.String(length=32), nullable=True),
            sa.Column("quantity", sa.Numeric(18, 4), nullable=True),
            sa.Column("unit", sa.String(length=32), nullable=True),
            sa.Column("unit_price", sa.Numeric(18, 4), nullable=True),
            sa.Column("discount_amount", sa.Numeric(18, 2), nullable=True),
            sa.Column("taxable_amount", sa.Numeric(18, 2), nullable=True),
            sa.Column("tax_rate", sa.Numeric(8, 4), nullable=True),
            sa.Column("tax_amount", sa.Numeric(18, 2), nullable=True),
            sa.Column("line_total", sa.Numeric(18, 2), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["submission_id"], ["bharathi_bill_submissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_bharathi_inv_lines_submission",
            "bharathi_purchase_invoice_lines",
            ["tenant_id", "submission_id"],
        )

    if not insp.has_table("bharathi_bill_ocr_jobs"):
        op.create_table(
            "bharathi_bill_ocr_jobs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("submission_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("provider", sa.String(length=64), nullable=True),
            sa.Column("model_name", sa.String(length=64), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["submission_id"], ["bharathi_bill_submissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_bharathi_ocr_jobs_submission",
            "bharathi_bill_ocr_jobs",
            ["tenant_id", "submission_id"],
        )

    if insp.has_table("bharathi_bill_submissions") and bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_bharathi_active_invoice_business_key
            ON bharathi_bill_submissions (tenant_id, supplier_identity_key, invoice_number_norm)
            WHERE supplier_identity_key IS NOT NULL
              AND invoice_number_norm IS NOT NULL
              AND status = ANY(ARRAY[
                'DRAFT','SUBMITTED','OCR_PROCESSING','EXTRACTED','NEEDS_REVIEW',
                'PENDING_VERIFICATION','VERIFIED','APPROVED','DUPLICATE_REVIEW','SYNC_PENDING'
              ])
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS uq_bharathi_active_invoice_business_key")
    if insp.has_table("bharathi_bill_ocr_jobs"):
        op.drop_table("bharathi_bill_ocr_jobs")
    if insp.has_table("bharathi_purchase_invoice_lines"):
        op.drop_table("bharathi_purchase_invoice_lines")