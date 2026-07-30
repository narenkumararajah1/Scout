"""add executives to company_snapshots

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-30

Executive movement tracking (V3 Enhancements Phase 4). Nullable with no
server default on purpose: snapshots captured before this phase had no
executive data at all, and NULL records that honestly where an empty list
would assert the company had no executives at capture time. The change
detector treats NULL as "unknown" and reports nothing, so existing
history produces no retroactive false movements.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "company_snapshots",
        sa.Column("executives", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("company_snapshots", "executives")
