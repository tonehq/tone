"""Add agent_llm_eval_results table for per-agent LLM output scoring.

Stores one row per scenario per run of the agent-LLM eval harness
(``evals/agent_llm_eval.py`` → ``AgentLlmEvalService``). Namespaced with
``agent_llm_`` so future ``agent_call_eval_results`` /
``agent_tool_eval_results`` fit alongside without renaming.

Typed columns (``llm_model``, ``llm_provider``, ``system_prompt``) +
``llm_settings_snapshot`` JSONB stamp the agent's config at run time so
scores stay attributable to a specific agent version even after the live
config changes.

Zero blast-radius on existing functionality: additive only, no FK from
existing tables into the new one. ``downgrade()`` drops cleanly.

Revision ID: c7e2a5b8f4d9
Revises: b2f9e4c1d7a3
Create Date: 2026-08-19 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c7e2a5b8f4d9"
down_revision = "b2f9e4c1d7a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_llm_eval_results",
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
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("triggered_by", sa.String(length=32), nullable=False),
        sa.Column("scenario_key", sa.String(length=120), nullable=False),
        sa.Column(
            "scenario_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.String(length=120), nullable=True),
        sa.Column("llm_provider", sa.String(length=60), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column(
            "llm_settings_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("judge_model", sa.String(length=120), nullable=True),
        sa.Column("judge_engine", sa.String(length=32), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="completed",
        ),
        sa.Column("actual_answer", sa.Text(), nullable=True),
        sa.Column("verdict", sa.String(length=16), nullable=True),
        sa.Column(
            "metric_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("judge_reasoning", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("answer_error", sa.Text(), nullable=True),
        sa.Column("judge_error", sa.Text(), nullable=True),
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
        sa.UniqueConstraint(
            "run_id", "scenario_key", name="uq_agent_llm_eval_results_run_scenario"
        ),
    )
    op.create_index(
        "ix_agent_llm_eval_results_organization_id",
        "agent_llm_eval_results",
        ["organization_id"],
    )
    op.create_index(
        "ix_agent_llm_eval_results_agent_id",
        "agent_llm_eval_results",
        ["agent_id"],
    )
    op.create_index(
        "ix_agent_llm_eval_results_agent_run_desc",
        "agent_llm_eval_results",
        ["agent_id", sa.text("run_number DESC")],
    )
    op.create_index(
        "ix_agent_llm_eval_results_run_id",
        "agent_llm_eval_results",
        ["run_id"],
    )
    op.create_index(
        "ix_agent_llm_eval_results_agent_verdict",
        "agent_llm_eval_results",
        ["agent_id", "verdict"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_llm_eval_results_agent_verdict",
        table_name="agent_llm_eval_results",
    )
    op.drop_index(
        "ix_agent_llm_eval_results_run_id",
        table_name="agent_llm_eval_results",
    )
    op.drop_index(
        "ix_agent_llm_eval_results_agent_run_desc",
        table_name="agent_llm_eval_results",
    )
    op.drop_index(
        "ix_agent_llm_eval_results_agent_id",
        table_name="agent_llm_eval_results",
    )
    op.drop_index(
        "ix_agent_llm_eval_results_organization_id",
        table_name="agent_llm_eval_results",
    )
    op.drop_table("agent_llm_eval_results")
