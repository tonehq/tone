"""replace per-line pipeline_logs with per-call call_pipeline_logs (JSON array)

Drops the per-line ``pipeline_logs`` table (its rows are discarded — they
re-populate on the next sync) and creates ``call_pipeline_logs``, which stores
ALL of a call's log lines as a single ``logs`` JSONB array on ONE row keyed by
``call_id`` (UNIQUE). The per-call viewer now reads one row; a re-sync replaces
the array wholesale. Idempotency comes from the bounded per-call fetch window,
so no per-line ``fingerprint`` unique key is needed anymore.

See ``core/models/log_entry.py`` (``CallPipelineLog``) and
``PipelineLogSyncService``.

Revision ID: d4b2f8a1c6e3
Revises: a1c9f4e7b2d5
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d4b2f8a1c6e3"
down_revision = "a1c9f4e7b2d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Discard the per-line table entirely (existing rows are not migrated —
    # they re-populate from Loki on the next per-call sync).
    op.drop_index("ix_pipeline_logs_call_ts", table_name="pipeline_logs")
    op.drop_table("pipeline_logs")

    op.create_table(
        "call_pipeline_logs",
        # OrgScopedModel columns.
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # Identity — stamped from the Call. One row per call.
        sa.Column(
            "call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("trace_id", sa.String(128), nullable=True, index=True),
        # All of the call's lines as one time-ordered JSON array.
        sa.Column(
            "logs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        # One row per call → the upsert conflict target and the viewer lookup key.
        # The UNIQUE constraint's index also serves call_id lookups (no separate index).
        sa.UniqueConstraint("call_id", name="uq_call_pipeline_logs_call_id"),
    )


def downgrade() -> None:
    op.drop_table("call_pipeline_logs")

    # Recreate the per-line table exactly as a1c9f4e7b2d5 created it.
    op.create_table(
        "pipeline_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calls.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("trace_id", sa.String(128), nullable=True, index=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("ts_ns", sa.BigInteger(), nullable=False),
        sa.Column("level", sa.String(16), nullable=True),
        sa.Column("logger_name", sa.String(255), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("raw_line", sa.Text(), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.UniqueConstraint("fingerprint", name="uq_pipeline_logs_fingerprint"),
    )
    op.create_index("ix_pipeline_logs_call_ts", "pipeline_logs", ["call_id", "ts"])
