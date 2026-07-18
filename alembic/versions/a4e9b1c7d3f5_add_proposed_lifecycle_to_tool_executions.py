"""add proposed_at and tool_call_id to tool_executions

Extends the tool_executions lifecycle model to capture *every* tool call the LLM
proposes during a call — including ones that never actually execute (LLM
hallucinated an unregistered tool name, user interrupted before dispatch, etc.).

* ``proposed_at`` — set the moment pipecat pushes ``FunctionCallsStartedFrame``
  for the tool_call_id; populated for every LLM proposal even if the handler
  never runs.
* ``tool_call_id`` — pipecat's per-call correlation id (``FunctionCallFromLLM``).
  Used to match a proposal to its later in-progress / result / cancel frames
  so proposal and execution telemetry land on the same row.

The ``status`` column now spans the full lifecycle (``proposed | cancelled |
success | error``); no schema-level check constraint so future values can be
added without a migration.

Existing rows keep NULL for both new columns — the ToolExecution serialization
already returns null-safe values.

Revision ID: a4e9b1c7d3f5
Revises: c5d9a4e7b2f1
Create Date: 2026-07-18

"""
from alembic import op
import sqlalchemy as sa


revision = "a4e9b1c7d3f5"
down_revision = "c5d9a4e7b2f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tool_executions",
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tool_executions",
        sa.Column("tool_call_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_tool_executions_tool_call_id",
        "tool_executions",
        ["tool_call_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tool_executions_tool_call_id", table_name="tool_executions")
    op.drop_column("tool_executions", "tool_call_id")
    op.drop_column("tool_executions", "proposed_at")
