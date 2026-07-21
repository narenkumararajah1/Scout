"""create evidence table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evidence_entity_type", "evidence", ["entity_type"])
    op.create_index("ix_evidence_entity_id", "evidence", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_entity_id", table_name="evidence")
    op.drop_index("ix_evidence_entity_type", table_name="evidence")
    op.drop_table("evidence")
