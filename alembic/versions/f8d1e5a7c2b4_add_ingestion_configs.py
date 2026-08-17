"""Add ingestion_configs table + ingestion_config_id FK + embedding_config JSONB

New named, reusable ingestion pipeline recipes. Selecting one when starting a
run snapshots every field onto the resulting ``ingestion_pipeline_runs`` row —
existing recipe columns on the run remain the source of truth so this change
is purely additive and safe for historical rows.

- ``ingestion_configs``: new org-scoped table with soft-delete
  (``deleted_at``) + ``(organization_id, name)`` uniqueness.
- ``ingestion_pipeline_runs.ingestion_config_id``: nullable FK with
  ``ON DELETE SET NULL`` — a deleted config never deletes its historical runs.
- ``embedding_config`` (JSONB, nullable) added to BOTH tables so per-provider
  embedder kwargs (batch_size, max_retries, tokens_per_minute, …) can be
  stored on a saved config and snapshotted onto the run row exactly like
  ``parser_config`` / ``tokeniser_config`` / ``vector_store_ref``.

Revision ID: f8d1e5a7c2b4
Revises: e9b3a2f7c4d1
Create Date: 2026-08-17 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f8d1e5a7c2b4"
down_revision = "e9b3a2f7c4d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("parser", sa.String(length=50), nullable=False),
        sa.Column(
            "parser_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("tokeniser", sa.String(length=50), nullable=False),
        sa.Column(
            "tokeniser_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("embedding_provider", sa.String(length=50), nullable=False),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding_version", sa.String(length=50), nullable=True),
        sa.Column(
            "embedding_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("vector_store", sa.String(length=32), nullable=False),
        sa.Column(
            "vector_store_ref",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
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
        sa.UniqueConstraint(
            "organization_id", "name", name="uq_ingestion_configs_org_name"
        ),
    )
    op.create_index(
        "ix_ingestion_configs_organization_id",
        "ingestion_configs",
        ["organization_id"],
    )
    op.create_index(
        "ix_ingestion_configs_org_active",
        "ingestion_configs",
        ["organization_id", "is_active"],
    )

    op.add_column(
        "ingestion_pipeline_runs",
        sa.Column(
            "ingestion_config_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "ingestion_pipeline_runs",
        sa.Column(
            "embedding_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_ingestion_pipeline_runs_ingestion_config_id",
        "ingestion_pipeline_runs",
        "ingestion_configs",
        ["ingestion_config_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_ingestion_pipeline_runs_ingestion_config_id",
        "ingestion_pipeline_runs",
        ["ingestion_config_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ingestion_pipeline_runs_ingestion_config_id",
        table_name="ingestion_pipeline_runs",
    )
    op.drop_constraint(
        "fk_ingestion_pipeline_runs_ingestion_config_id",
        "ingestion_pipeline_runs",
        type_="foreignkey",
    )
    op.drop_column("ingestion_pipeline_runs", "embedding_config")
    op.drop_column("ingestion_pipeline_runs", "ingestion_config_id")

    op.drop_index("ix_ingestion_configs_org_active", table_name="ingestion_configs")
    op.drop_index(
        "ix_ingestion_configs_organization_id", table_name="ingestion_configs"
    )
    op.drop_table("ingestion_configs")
