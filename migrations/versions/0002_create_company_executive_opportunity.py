"""create company, executive, opportunity tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("industry", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("headquarters", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=255), nullable=True),
        sa.Column("employee_count", sa.Integer(), nullable=True),
        sa.Column("revenue_range", sa.String(length=100), nullable=True),
        sa.Column("business_segments", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="enabled"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "executives",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("biography", sa.String(), nullable=True),
        sa.Column("responsibilities", postgresql.JSONB(), nullable=True),
        sa.Column("business_priorities", postgresql.JSONB(), nullable=True),
        sa.Column("technology_focus", postgresql.JSONB(), nullable=True),
        sa.Column("linkedin_url", sa.String(length=500), nullable=True),
        sa.Column("contact_information", sa.String(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_executives_company_id", "executives", ["company_id"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("research_session_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("opportunity_score", sa.Float(), nullable=True),
        sa.Column("business_impact", sa.String(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("supporting_evidence", postgresql.JSONB(), nullable=True),
        sa.Column("reasoning", sa.String(), nullable=True),
        sa.Column("recommended_actions", postgresql.JSONB(), nullable=True),
        sa.Column("supporting_signal_ids", postgresql.JSONB(), nullable=True),
        sa.Column("capability_match_ids", postgresql.JSONB(), nullable=True),
        sa.Column("recommended_services", postgresql.JSONB(), nullable=True),
        sa.Column("recommended_case_studies", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_opportunities_company_id", "opportunities", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_company_id", table_name="opportunities")
    op.drop_table("opportunities")
    op.drop_index("ix_executives_company_id", table_name="executives")
    op.drop_table("executives")
    op.drop_table("companies")
