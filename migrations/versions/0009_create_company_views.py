"""create company_views table

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_views",
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), primary_key=True),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("company_views")
