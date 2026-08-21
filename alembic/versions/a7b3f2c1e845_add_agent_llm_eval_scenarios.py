"""add agent_llm_eval_scenarios table + v2 forward-compat columns on agent_llm_eval_results

Adds:
- New ``agent_llm_eval_scenarios`` table storing per-agent Level 2 (agent-LLM
  eval) test cases. Users create scenarios (prompt + optional expected answer
  + optional GEval rubrics) manually, from CSV, or from a future generator.
  ``AgentLlmEvalService.run_eval_for_agent`` loads rows from this table,
  converts each to the in-memory ``LLMScenario`` dataclass, and passes them
  to the existing ``run_eval`` codepath — so the CLI's fixture-driven path
  keeps working unchanged.
- Two nullable JSONB columns on ``agent_llm_eval_results`` (``execution_trace``,
  ``tools_called``) reserved for a future v2 tool/MCP-scoring runner. Both
  stay ``NULL`` for every v1 row; existing writers/readers are unchanged.

Zero-blast-radius: the new table starts empty for every org (so no existing
agent sees behavior change), and the two additive columns are nullable + no
default (so every existing INSERT/SELECT keeps working). Guards mirror
``d9e4f1a6b8c2_add_eval_settings_to_organizations.py`` so re-running is safe.

Revision ID: a7b3f2c1e845
Revises: d9e4f1a6b8c2
Create Date: 2026-08-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "a7b3f2c1e845"
down_revision = "d9e4f1a6b8c2"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspect(op.get_bind()).get_columns(table))


def _has_index(table: str, index: str) -> bool:
    # ``get_indexes`` raises ``NoSuchTableError`` when the table is gone,
    # which happens on a partially-completed downgrade re-run — guard here
    # so callers can be written as simple booleans.
    if not _has_table(table):
        return False
    return any(i["name"] == index for i in inspect(op.get_bind()).get_indexes(table))


def upgrade() -> None:
    if not _has_table("agent_llm_eval_scenarios"):
        op.create_table(
            "agent_llm_eval_scenarios",
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
                nullable=False,
            ),
            sa.Column("scenario_key", sa.String(length=120), nullable=False),
            sa.Column(
                "scenario_ord",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("expected_answer", sa.Text(), nullable=True),
            sa.Column("persona_criteria", sa.Text(), nullable=True),
            sa.Column("instruction_criteria", sa.Text(), nullable=True),
            sa.Column(
                "tags",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column(
                "metrics_override",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column("threshold_override", sa.Float(), nullable=True),
            sa.Column(
                "source",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'manual'"),
            ),
            sa.Column(
                "generation_metadata",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            # v2 forward-compat — reserved for expected tool-call traces and
            # per-scenario tool/MCP config the future tool-scoring runner
            # will read. Nullable so v1 writers ignore them.
            sa.Column(
                "expected_tools",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column(
                "tool_config",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["agent_id"], ["agents.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint(
                "agent_id",
                "scenario_key",
                name="uq_agent_llm_eval_scenarios_agent_key",
            ),
        )

    if not _has_index(
        "agent_llm_eval_scenarios", "ix_agent_llm_eval_scenarios_organization_id"
    ):
        op.create_index(
            "ix_agent_llm_eval_scenarios_organization_id",
            "agent_llm_eval_scenarios",
            ["organization_id"],
        )

    # No standalone ``agent_id`` index — Postgres serves single-column
    # ``agent_id`` lookups from the leftmost prefix of the compound
    # ``(agent_id, scenario_ord)`` below, so a second index would just be
    # write overhead.
    if not _has_index(
        "agent_llm_eval_scenarios", "ix_agent_llm_eval_scenarios_agent_ord"
    ):
        op.create_index(
            "ix_agent_llm_eval_scenarios_agent_ord",
            "agent_llm_eval_scenarios",
            ["agent_id", "scenario_ord"],
        )

    if not _has_column("agent_llm_eval_results", "execution_trace"):
        op.add_column(
            "agent_llm_eval_results",
            sa.Column(
                "execution_trace",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )

    if not _has_column("agent_llm_eval_results", "tools_called"):
        op.add_column(
            "agent_llm_eval_results",
            sa.Column(
                "tools_called",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )


def downgrade() -> None:
    if _has_column("agent_llm_eval_results", "tools_called"):
        op.drop_column("agent_llm_eval_results", "tools_called")
    if _has_column("agent_llm_eval_results", "execution_trace"):
        op.drop_column("agent_llm_eval_results", "execution_trace")

    if _has_index(
        "agent_llm_eval_scenarios", "ix_agent_llm_eval_scenarios_agent_ord"
    ):
        op.drop_index(
            "ix_agent_llm_eval_scenarios_agent_ord",
            table_name="agent_llm_eval_scenarios",
        )
    if _has_index(
        "agent_llm_eval_scenarios", "ix_agent_llm_eval_scenarios_organization_id"
    ):
        op.drop_index(
            "ix_agent_llm_eval_scenarios_organization_id",
            table_name="agent_llm_eval_scenarios",
        )
    if _has_table("agent_llm_eval_scenarios"):
        op.drop_table("agent_llm_eval_scenarios")
