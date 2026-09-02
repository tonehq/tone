"""add hot-path FK indexes on agent_tools, agent_mcp_servers, phone_numbers

Adds b-tree indexes on frequently-joined foreign-key columns that were
previously unindexed:

- agent_tools.agent_id
- agent_tools.tool_id
- agent_mcp_servers.agent_id
- agent_mcp_servers.mcp_server_id
- phone_numbers.agent_id

These back per-agent tool/MCP fan-out and inbound number → agent routing.
Each create is guarded by _has_index so re-running is a no-op, and the
downgrade drops exactly the five indexes this migration adds.

Revision ID: d9f4a1c7b2e5
Revises: c4a7e2f8b1d9
Create Date: 2026-09-02 00:00:00.000000
"""
from alembic import op
from sqlalchemy import inspect


revision = "d9f4a1c7b2e5"
down_revision = "c4a7e2f8b1d9"
branch_labels = None
depends_on = None


# (index_name, table_name, [columns])
_INDEXES = [
    ("ix_agent_tools_agent_id", "agent_tools", ["agent_id"]),
    ("ix_agent_tools_tool_id", "agent_tools", ["tool_id"]),
    ("ix_agent_mcp_servers_agent_id", "agent_mcp_servers", ["agent_id"]),
    ("ix_agent_mcp_servers_mcp_server_id", "agent_mcp_servers", ["mcp_server_id"]),
    ("ix_phone_numbers_agent_id", "phone_numbers", ["agent_id"]),
]


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_index(table: str, index: str) -> bool:
    if not _has_table(table):
        return False
    return any(i["name"] == index for i in inspect(op.get_bind()).get_indexes(table))


def upgrade() -> None:
    for index_name, table_name, columns in _INDEXES:
        if not _has_index(table_name, index_name):
            op.create_index(index_name, table_name, columns)


def downgrade() -> None:
    for index_name, table_name, _columns in reversed(_INDEXES):
        if _has_index(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
