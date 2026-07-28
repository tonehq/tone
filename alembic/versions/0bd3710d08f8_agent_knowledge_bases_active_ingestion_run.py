"""agent_knowledge_bases: add active_ingestion_pipeline_run_id (per-agent run pin)

Adds a nullable FK on ``agent_knowledge_bases`` so an agent can pin a specific
``ingestion_pipeline_runs`` row for a KB instead of always following the KB
default. NULL means "follow KB default"; SET NULL on run delete so a pinned
run being removed silently falls back — matches the resolver's fallback chain
in ``IngestionRunService.resolve_active_run_id``.

Revision ID: 0bd3710d08f8
Revises: 7821c3c4d7b5
Create Date: 2026-07-28 00:10:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0bd3710d08f8"
down_revision = "7821c3c4d7b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_knowledge_bases",
        sa.Column(
            "active_ingestion_pipeline_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_agent_knowledge_bases_active_ingestion_pipeline_run_id"),
        "agent_knowledge_bases",
        ["active_ingestion_pipeline_run_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_agent_knowledge_bases_active_ingestion_pipeline_run_id",
        "agent_knowledge_bases",
        "ingestion_pipeline_runs",
        ["active_ingestion_pipeline_run_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_agent_knowledge_bases_active_ingestion_pipeline_run_id",
        "agent_knowledge_bases",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_agent_knowledge_bases_active_ingestion_pipeline_run_id"),
        table_name="agent_knowledge_bases",
    )
    op.drop_column("agent_knowledge_bases", "active_ingestion_pipeline_run_id")
