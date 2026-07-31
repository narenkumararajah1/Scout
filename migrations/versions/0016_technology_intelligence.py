"""technology intelligence: observation tracking

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-31

Replaces the removed snapshot-diff approach to technology change
detection (see TECH_DEBT.md). Diffing two consecutive extractions was
measured at 0.15 Jaccard stability on an unchanged company, so
differences between runs described the extractor, not the business.
These columns accumulate observations instead, which is immune to
sampling: a technology's history is the record of every time Scout saw
it, not the difference between the last two times it looked.

Backfill is deliberate rather than left NULL. Existing rows already
represent at least one real observation, so they are seeded with
observation_count = 1 and first/last seen set to the row's own
timestamps. Leaving them NULL would make every previously-known
technology look newly detected on the next run - the exact false-signal
class this work exists to remove.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("technologies", sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("technologies", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "technologies",
        sa.Column("observation_count", sa.Integer(), nullable=False, server_default="0"),
    )
    # Two miss counters, because they answer different questions and
    # conflating them overstates confidence: a technology seen and missed
    # alternately has a true observation rate of 50%, but a counter that
    # resets on every sighting would report it as near 1.0.
    op.add_column(
        "technologies",
        sa.Column("missed_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "technologies",
        sa.Column("consecutive_misses", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("technologies", sa.Column("observation_sources", postgresql.JSONB(), nullable=True))

    # Seed existing rows from their own timestamps - see the module
    # docstring on why NULL would manufacture false "newly detected".
    op.execute(
        """
        UPDATE technologies
           SET first_seen_at = created_at,
            last_seen_at = COALESCE(updated_at, created_at),
            observation_count = 1
        """
    )


def downgrade() -> None:
    op.drop_column("technologies", "observation_sources")
    op.drop_column("technologies", "consecutive_misses")
    op.drop_column("technologies", "missed_count")
    op.drop_column("technologies", "observation_count")
    op.drop_column("technologies", "last_seen_at")
    op.drop_column("technologies", "first_seen_at")
