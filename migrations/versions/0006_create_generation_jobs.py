"""create generation_jobs table

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("input_params", postgresql.JSONB(), nullable=True),
        sa.Column("result_id", sa.String(length=36), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("progress_message", sa.String(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_generation_jobs_company_id", "generation_jobs", ["company_id"])
    # Supports the active-job lookup used for generation rate limiting
    # (Priority 7): "is there already a pending/running job of this type
    # for this company?".
    op.create_index("ix_generation_jobs_company_type_status", "generation_jobs", ["company_id", "job_type", "status"])


def downgrade() -> None:
    op.drop_index("ix_generation_jobs_company_type_status", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_company_id", table_name="generation_jobs")
    op.drop_table("generation_jobs")
