"""add tool_executions table

Stores one row per tool / MCP-tool invocation during a call (tool name, type,
MCP server, arguments, result, status, error, status code, duration, turn) so
tool calls are queryable for debugging. Mirrors the OrgScopedModel convention:
UUID PK, organization_id as a plain indexed UUID, timezone-aware timestamps.

Revision ID: b7e1c0a2d9f3
Revises: 863e72f0e55a
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b7e1c0a2d9f3'
down_revision = '863e72f0e55a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tool_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("tool_name", sa.String(255), nullable=False),
        sa.Column("tool_type", sa.String(50), nullable=True),
        sa.Column("mcp_server_name", sa.String(255), nullable=True),
        sa.Column("arguments", postgresql.JSONB(), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("turn_number", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("tool_executions")
