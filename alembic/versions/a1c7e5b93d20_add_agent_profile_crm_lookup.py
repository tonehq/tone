"""add CRM lookup for profile variables

Two additive changes for the "fill empty profile variables from a connected
CRM (MCP) at call start" feature:

1. ``agent_profile_variables.crm_field`` — nullable dot-path into the CRM
   lookup response that fills a variable when its ``value`` is empty
   (e.g. ``properties.firstname``). NULL for every existing row.
2. ``agent_profile_crm_config`` — one row per agent holding the lookup
   settings (which CRM server + tool + phone argument + on/off).

Zero-blast-radius: the new column is nullable and the new table starts empty
with ``is_enabled`` defaulting to false, so every existing agent behaves
exactly as before until someone configures CRM enrichment. Guards mirror
``c9e2a1f8b4d7_add_agent_profile_variables`` so re-running is safe.

Revision ID: a1c7e5b93d20
Revises: f3b8d1e0c6a9
Create Date: 2026-09-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "a1c7e5b93d20"
down_revision = "f3b8d1e0c6a9"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(c["name"] == column for c in inspect(op.get_bind()).get_columns(table))


def _has_index(table: str, index: str) -> bool:
    if not _has_table(table):
        return False
    return any(i["name"] == index for i in inspect(op.get_bind()).get_indexes(table))


def upgrade() -> None:
    if _has_table("agent_profile_variables") and not _has_column(
        "agent_profile_variables", "crm_field"
    ):
        op.add_column(
            "agent_profile_variables",
            sa.Column("crm_field", sa.String(length=200), nullable=True),
        )

    if not _has_table("agent_profile_crm_config"):
        op.create_table(
            "agent_profile_crm_config",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "organization_id", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("mcp_server_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("lookup_tool_name", sa.String(length=200), nullable=True),
            sa.Column("phone_argument", sa.String(length=120), nullable=True),
            sa.Column(
                "is_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
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
            sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["mcp_server_id"], ["mcp_servers.id"], ondelete="SET NULL"
            ),
            sa.UniqueConstraint(
                "agent_id", name="uq_agent_profile_crm_config_agent"
            ),
        )

    if not _has_index(
        "agent_profile_crm_config", "ix_agent_profile_crm_config_organization_id"
    ):
        op.create_index(
            "ix_agent_profile_crm_config_organization_id",
            "agent_profile_crm_config",
            ["organization_id"],
        )


def downgrade() -> None:
    if _has_index(
        "agent_profile_crm_config", "ix_agent_profile_crm_config_organization_id"
    ):
        op.drop_index(
            "ix_agent_profile_crm_config_organization_id",
            table_name="agent_profile_crm_config",
        )
    if _has_table("agent_profile_crm_config"):
        op.drop_table("agent_profile_crm_config")

    if _has_column("agent_profile_variables", "crm_field"):
        op.drop_column("agent_profile_variables", "crm_field")
