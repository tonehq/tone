"""Add optional name to ingestion_pipeline_runs

A human-friendly label for an ingestion run so the runs table + the eval
source-run picker are easy to scan (instead of only "Run #N"). Purely additive
and nullable — historical runs and blank submissions stay valid and the UI
falls back to "Run #<run_number>".

Revision ID: c7f1a3d9b6e2
Revises: b2e8f4a1c9d5
Create Date: 2026-09-09 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "c7f1a3d9b6e2"
down_revision = "b2e8f4a1c9d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingestion_pipeline_runs",
        sa.Column("name", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ingestion_pipeline_runs", "name")
