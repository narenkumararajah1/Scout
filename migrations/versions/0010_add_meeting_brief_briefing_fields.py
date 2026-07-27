"""add recent_developments/risks/related_opportunities to meeting_briefs

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("meeting_briefs", sa.Column("recent_developments", postgresql.JSONB(), nullable=True))
    op.add_column("meeting_briefs", sa.Column("risks", postgresql.JSONB(), nullable=True))
    op.add_column("meeting_briefs", sa.Column("related_opportunities", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("meeting_briefs", "related_opportunities")
    op.drop_column("meeting_briefs", "risks")
    op.drop_column("meeting_briefs", "recent_developments")
