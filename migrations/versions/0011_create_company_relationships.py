"""create company_relationships table

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_relationships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("related_company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("related_company_name", sa.String(length=255), nullable=True),
        sa.Column("relationship_type", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_company_relationships_company_id", "company_relationships", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_company_relationships_company_id", table_name="company_relationships")
    op.drop_table("company_relationships")
