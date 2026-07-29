"""create company_snapshots table

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("research_session_id", sa.String(length=36), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("signals", postgresql.JSONB(), nullable=True),
        sa.Column("opportunities", postgresql.JSONB(), nullable=True),
        sa.Column("capabilities", postgresql.JSONB(), nullable=True),
        sa.Column("profile", postgresql.JSONB(), nullable=True),
        sa.Column("signal_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opportunity_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detected_changes", postgresql.JSONB(), nullable=True),
        sa.Column("change_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary_narrative", sa.String(), nullable=True),
        sa.Column("recommended_actions", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_company_snapshots_company_id", "company_snapshots", ["company_id"])
    # Every read is "the latest (or previous) snapshot for this company",
    # so the index that matters is the composite one, descending on time.
    op.create_index(
        "ix_company_snapshots_company_captured",
        "company_snapshots",
        ["company_id", sa.text("captured_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_company_snapshots_company_captured", table_name="company_snapshots")
    op.drop_index("ix_company_snapshots_company_id", table_name="company_snapshots")
    op.drop_table("company_snapshots")
