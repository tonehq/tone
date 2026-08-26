"""add agent_profile_variables table

Adds a per-agent key/value/description store for the Agent Profile Variables
feature. Users create variables (e.g. ``customer_name = "Acme Corp"``) and
reference them anywhere the prompt/workflow substitutes ``{{...}}`` tokens as
``{{profile.<key>}}``. Resolution reuses the existing
``core/services/pipeline/prompt_variables.py::substitute_variables`` code
path — no parallel templating engine.

Zero-blast-radius: the new table starts empty for every org, so no existing
agent's behavior changes. Guards mirror ``a7b3f2c1e845_add_agent_llm_eval_scenarios``
so re-running the migration is safe.

Revision ID: c9e2a1f8b4d7
Revises: b8f2a6d9c31e
Create Date: 2026-08-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "c9e2a1f8b4d7"
down_revision = "b8f2a6d9c31e"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_index(table: str, index: str) -> bool:
    if not _has_table(table):
        return False
    return any(i["name"] == index for i in inspect(op.get_bind()).get_indexes(table))


def upgrade() -> None:
    if not _has_table("agent_profile_variables"):
        op.create_table(
            "agent_profile_variables",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
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
            sa.Column("key", sa.String(length=64), nullable=False),
            sa.Column(
                "value",
                sa.Text(),
                nullable=False,
                server_default=sa.text("''"),
            ),
            sa.Column("description", sa.Text(), nullable=True),
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
                "agent_id", "key", name="uq_agent_profile_variables_agent_key"
            ),
        )

    if not _has_index(
        "agent_profile_variables", "ix_agent_profile_variables_organization_id"
    ):
        op.create_index(
            "ix_agent_profile_variables_organization_id",
            "agent_profile_variables",
            ["organization_id"],
        )

    if not _has_index("agent_profile_variables", "ix_agent_profile_variables_agent"):
        op.create_index(
            "ix_agent_profile_variables_agent",
            "agent_profile_variables",
            ["agent_id"],
        )


def downgrade() -> None:
    if _has_index("agent_profile_variables", "ix_agent_profile_variables_agent"):
        op.drop_index(
            "ix_agent_profile_variables_agent",
            table_name="agent_profile_variables",
        )
    if _has_index(
        "agent_profile_variables", "ix_agent_profile_variables_organization_id"
    ):
        op.drop_index(
            "ix_agent_profile_variables_organization_id",
            table_name="agent_profile_variables",
        )
    if _has_table("agent_profile_variables"):
        op.drop_table("agent_profile_variables")
