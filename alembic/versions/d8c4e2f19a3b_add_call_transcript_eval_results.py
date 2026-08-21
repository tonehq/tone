"""Add call_transcript_eval_results table for post-call transcript scoring.

Stores one DeepEval-scored transcript per completed call
(``EvalCallTranscriptAction`` → ``CallTranscriptEvalService`` → this table).
v1 is full-call only (``mode='full_call'``); the per-turn mode is reserved
via the ``turn_number`` column.

Snapshot columns (``llm_model``, ``llm_provider``, ``system_prompt``,
``chatbot_role``) stamp the agent's config at scoring time so a later config
edit cannot retroactively rewrite what was scored.

Zero blast-radius on existing functionality: additive only, no FK from
existing tables into the new one. ``downgrade()`` drops cleanly.

Revision ID: d8c4e2f19a3b
Revises: a7b3f2c1e845
Create Date: 2026-08-21 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d8c4e2f19a3b"
down_revision = "a7b3f2c1e845"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "call_transcript_eval_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_configs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "mode",
            sa.String(length=16),
            nullable=False,
            server_default="full_call",
        ),
        sa.Column("turn_number", sa.Integer(), nullable=True),
        sa.Column("llm_model", sa.String(length=120), nullable=True),
        sa.Column("llm_provider", sa.String(length=60), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("chatbot_role", sa.String(length=400), nullable=True),
        sa.Column("judge_model", sa.String(length=120), nullable=True),
        sa.Column("judge_engine", sa.String(length=32), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="completed",
        ),
        sa.Column("verdict", sa.String(length=16), nullable=True),
        sa.Column(
            "metric_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("judge_reasoning", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("judge_error", sa.Text(), nullable=True),
        sa.Column("skip_reason", sa.String(length=120), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "tool_trace",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "rag_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "mcp_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_call_transcript_eval_results_organization_id",
        "call_transcript_eval_results",
        ["organization_id"],
    )
    op.create_index(
        "ix_call_transcript_eval_results_agent_id",
        "call_transcript_eval_results",
        ["agent_id"],
    )
    op.create_index(
        "ix_call_transcript_eval_results_call_id",
        "call_transcript_eval_results",
        ["call_id"],
    )
    op.create_index(
        "ix_call_transcript_eval_results_agent_verdict",
        "call_transcript_eval_results",
        ["agent_id", "verdict"],
    )
    op.create_index(
        "ix_call_transcript_eval_results_call_mode",
        "call_transcript_eval_results",
        ["call_id", "mode"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_call_transcript_eval_results_call_mode",
        table_name="call_transcript_eval_results",
    )
    op.drop_index(
        "ix_call_transcript_eval_results_agent_verdict",
        table_name="call_transcript_eval_results",
    )
    op.drop_index(
        "ix_call_transcript_eval_results_call_id",
        table_name="call_transcript_eval_results",
    )
    op.drop_index(
        "ix_call_transcript_eval_results_agent_id",
        table_name="call_transcript_eval_results",
    )
    op.drop_index(
        "ix_call_transcript_eval_results_organization_id",
        table_name="call_transcript_eval_results",
    )
    op.drop_table("call_transcript_eval_results")
