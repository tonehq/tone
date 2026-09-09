"""add per-agent webhook data source for profile variables

Two additive changes for the "fill profile variables from a user HTTP webhook
at call start" feature (the generic replacement for the removed CRM lookup):

1. ``agent_profile_variables.source`` / ``source_path`` — mark a variable as
   webhook-sourced and where to read it from in the response. ``source``
   defaults to ``"static"`` (backfills every existing row → unchanged
   behavior); ``source_path`` is NULL for all existing rows.
2. ``agent_profile_webhooks`` — one row per agent holding the endpoint config
   (URL + method + encrypted headers + request identifiers + directions +
   timeout + on/off).

Zero-blast-radius: new columns are defaulted/nullable and the new table starts
empty, so every existing agent behaves exactly as before until a webhook is
configured. Guards mirror ``a1c7e5b93d20_add_agent_profile_crm_lookup`` so
re-running is safe.

Revision ID: c2a9f1e7b4d8
Revises: b4d2f7c1a9e3
Create Date: 2026-09-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "c2a9f1e7b4d8"
down_revision = "b4d2f7c1a9e3"
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
        "agent_profile_variables", "source"
    ):
        op.add_column(
            "agent_profile_variables",
            sa.Column(
                "source",
                sa.String(length=20),
                nullable=False,
                server_default="static",
            ),
        )
    if _has_table("agent_profile_variables") and not _has_column(
        "agent_profile_variables", "source_path"
    ):
        op.add_column(
            "agent_profile_variables",
            sa.Column("source_path", sa.String(length=200), nullable=True),
        )

    if not _has_table("agent_profile_webhooks"):
        op.create_table(
            "agent_profile_webhooks",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "organization_id", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("endpoint_url", sa.String(length=500), nullable=False),
            sa.Column(
                "http_method",
                sa.String(length=10),
                nullable=False,
                server_default="POST",
            ),
            sa.Column("headers", postgresql.JSONB(), nullable=True),
            sa.Column("request_identifiers", postgresql.JSONB(), nullable=True),
            sa.Column("directions", postgresql.JSONB(), nullable=True),
            sa.Column(
                "timeout_seconds",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("3"),
            ),
            sa.Column(
                "is_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
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
            sa.UniqueConstraint(
                "agent_id", name="uq_agent_profile_webhooks_agent"
            ),
        )

    if not _has_index(
        "agent_profile_webhooks", "ix_agent_profile_webhooks_organization_id"
    ):
        op.create_index(
            "ix_agent_profile_webhooks_organization_id",
            "agent_profile_webhooks",
            ["organization_id"],
        )


def downgrade() -> None:
    if _has_index(
        "agent_profile_webhooks", "ix_agent_profile_webhooks_organization_id"
    ):
        op.drop_index(
            "ix_agent_profile_webhooks_organization_id",
            table_name="agent_profile_webhooks",
        )
    if _has_table("agent_profile_webhooks"):
        op.drop_table("agent_profile_webhooks")

    if _has_column("agent_profile_variables", "source_path"):
        op.drop_column("agent_profile_variables", "source_path")
    if _has_column("agent_profile_variables", "source"):
        op.drop_column("agent_profile_variables", "source")
