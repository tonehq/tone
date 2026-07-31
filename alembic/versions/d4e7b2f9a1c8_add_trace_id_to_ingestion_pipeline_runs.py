"""Add trace_id to ingestion_pipeline_runs

Stamps every log line emitted during one ingestion run with a stable id
(``{short_uuid}-ing-{run_id}``) so the full log stream for one ingestion is
filterable by a single value — mirrors ``calls.trace_id`` for voice calls.
Generated + persisted by ``IngestionRunService.mark_running`` via
``core.logging.start_ingestion_trace``.

Purely additive: the column is nullable and unindexed rows created before
this migration continue to work. Not backfilled — historical runs never
emitted a trace_id in their logs, so a fabricated post-hoc id would not
match anything grepable.

Revision ID: d4e7b2f9a1c8
Revises: 0bd3710d08f8
Create Date: 2026-07-31 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "d4e7b2f9a1c8"
down_revision = "0bd3710d08f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingestion_pipeline_runs",
        sa.Column("trace_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_ingestion_pipeline_runs_trace_id",
        "ingestion_pipeline_runs",
        ["trace_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ingestion_pipeline_runs_trace_id",
        table_name="ingestion_pipeline_runs",
    )
    op.drop_column("ingestion_pipeline_runs", "trace_id")
