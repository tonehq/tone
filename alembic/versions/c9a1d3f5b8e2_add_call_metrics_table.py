"""add call_metrics table

Creates the ``call_metrics`` table that will hold per-call pipeline metrics
(ttfb, processing, llm_usage, tts_usage, user_bot_latency, turns) as six
JSONB columns, one row per call linked by a UNIQUE FK to ``calls.id``.

Pure DDL — does NOT migrate existing data. Historical metrics still live in
``calls.metadata['metrics']`` after this migration; run
``dev/backfill_call_metrics.py`` once the new code is live to copy them into
the new table and strip the legacy key.

Revision ID: c9a1d3f5b8e2
Revises: 9faf9806b065
Create Date: 2026-06-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c9a1d3f5b8e2'
down_revision = '9faf9806b065'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "call_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calls.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("ttfb", postgresql.JSONB(), nullable=True),
        sa.Column("processing", postgresql.JSONB(), nullable=True),
        sa.Column("llm_usage", postgresql.JSONB(), nullable=True),
        sa.Column("tts_usage", postgresql.JSONB(), nullable=True),
        sa.Column("user_bot_latency", postgresql.JSONB(), nullable=True),
        sa.Column("turns", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_call_metrics_org_call",
        "call_metrics",
        ["organization_id", "call_id"],
        unique=False,
    )
    op.create_index(
        "ix_call_metrics_created_at",
        "call_metrics",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_call_metrics_created_at", table_name="call_metrics")
    op.drop_index("ix_call_metrics_org_call", table_name="call_metrics")
    op.drop_table("call_metrics")
