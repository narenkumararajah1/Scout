"""create sales_playbook, meeting_brief, outreach_draft, v3 report tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sales_playbooks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=True),
        sa.Column("strategy_summary", sa.String(), nullable=True),
        sa.Column("discovery_questions", postgresql.JSONB(), nullable=True),
        sa.Column("talking_points", postgresql.JSONB(), nullable=True),
        sa.Column("objection_handling", postgresql.JSONB(), nullable=True),
        sa.Column("recommended_services", postgresql.JSONB(), nullable=True),
        sa.Column("next_steps", postgresql.JSONB(), nullable=True),
        sa.Column("risks", postgresql.JSONB(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sales_playbooks_company_id", "sales_playbooks", ["company_id"])

    op.create_table(
        "meeting_briefs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("meeting_title", sa.String(length=255), nullable=True),
        sa.Column("executive_summary", sa.String(), nullable=True),
        sa.Column("business_priorities", postgresql.JSONB(), nullable=True),
        sa.Column("executive_profiles", postgresql.JSONB(), nullable=True),
        sa.Column("talking_points", postgresql.JSONB(), nullable=True),
        sa.Column("discovery_questions", postgresql.JSONB(), nullable=True),
        sa.Column("recommended_services", postgresql.JSONB(), nullable=True),
        sa.Column("meeting_objectives", postgresql.JSONB(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_meeting_briefs_company_id", "meeting_briefs", ["company_id"])

    op.create_table(
        "outreach_drafts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_outreach_drafts_company_id", "outreach_drafts", ["company_id"])

    op.create_table(
        "v3_reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("report_type", sa.String(length=50), nullable=False, server_default="full_intelligence"),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("executive_summary", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Generated"),
        sa.Column("content", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_v3_reports_company_id", "v3_reports", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_v3_reports_company_id", table_name="v3_reports")
    op.drop_table("v3_reports")
    op.drop_index("ix_outreach_drafts_company_id", table_name="outreach_drafts")
    op.drop_table("outreach_drafts")
    op.drop_index("ix_meeting_briefs_company_id", table_name="meeting_briefs")
    op.drop_table("meeting_briefs")
    op.drop_index("ix_sales_playbooks_company_id", table_name="sales_playbooks")
    op.drop_table("sales_playbooks")
