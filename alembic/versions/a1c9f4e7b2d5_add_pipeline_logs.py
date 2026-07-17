"""add pipeline_logs (per-call Loki log read-back)

New ``pipeline_logs`` table storing a finished call's log lines read back from
Grafana Loki, to power an in-product per-call log viewer. Identity columns are
stamped from the ``calls`` row; ``fingerprint`` is UNIQUE so re-syncs are
idempotent (``on_conflict_do_nothing``). Rows CASCADE-delete with their call.

See ``core/models/log_entry.py`` and ``PipelineLogSyncService``.

Revision ID: a1c9f4e7b2d5
Revises: c3e5a7b9d1f4
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a1c9f4e7b2d5"
down_revision = "c3e5a7b9d1f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_logs",
        # OrgScopedModel columns.
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # Identity — stamped from the Call.
        sa.Column(
            "call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calls.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("trace_id", sa.String(128), nullable=True, index=True),
        # Line timestamp.
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("ts_ns", sa.BigInteger(), nullable=False),
        # Parsed (defensive) fields.
        sa.Column("level", sa.String(16), nullable=True),
        sa.Column("logger_name", sa.String(255), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        # Verbatim line + Loki stream labels.
        sa.Column("raw_line", sa.Text(), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Dedup key.
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.UniqueConstraint("fingerprint", name="uq_pipeline_logs_fingerprint"),
    )
    # Primary viewer access path: a call's lines in time order.
    op.create_index("ix_pipeline_logs_call_ts", "pipeline_logs", ["call_id", "ts"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_logs_call_ts", table_name="pipeline_logs")
    op.drop_table("pipeline_logs")
