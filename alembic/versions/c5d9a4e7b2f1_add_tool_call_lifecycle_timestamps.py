"""add llm_requested_at / invoked_at / completed_at to tool_executions

Splits the single ``started_at`` moment into three explicit lifecycle timestamps
so we can measure both LLM→dispatch latency and handler duration per tool call:

* ``llm_requested_at`` — pipecat's ``FunctionCallInProgress`` frame (LLM decided to call)
* ``invoked_at``       — handler body actually began executing
* ``completed_at``     — handler returned (success or error)

``started_at`` + ``duration_ms`` stay for backward compatibility — dual-written by
the handlers so existing readers keep working.

Revision ID: c5d9a4e7b2f1
Revises: b8f13d0a5c72
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa


revision = "c5d9a4e7b2f1"
down_revision = "b8f13d0a5c72"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tool_executions",
        sa.Column("llm_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tool_executions",
        sa.Column("invoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tool_executions",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tool_executions", "completed_at")
    op.drop_column("tool_executions", "invoked_at")
    op.drop_column("tool_executions", "llm_requested_at")
