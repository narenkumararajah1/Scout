"""create generation_feedback table

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generation_feedback",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("target_type", sa.String(length=30), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("rating", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_generation_feedback_target", "generation_feedback", ["target_type", "target_id"])


def downgrade() -> None:
    op.drop_index("ix_generation_feedback_target", table_name="generation_feedback")
    op.drop_table("generation_feedback")
