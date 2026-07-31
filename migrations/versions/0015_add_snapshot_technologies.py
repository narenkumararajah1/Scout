"""add technologies to company_snapshots

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-30

Technology adoption tracking (V3 Enhancements Phase 7B). Same reasoning
as 0014's executives column: nullable with no server default, because
snapshots captured before this phase genuinely did not look at
technologies and NULL says so, where an empty list would assert the
company used none. The detector treats NULL as "unknown" and reports
nothing, so existing history produces no retroactive false adoptions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "company_snapshots",
        sa.Column("technologies", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("company_snapshots", "technologies")
