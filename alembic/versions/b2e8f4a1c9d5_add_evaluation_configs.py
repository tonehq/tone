"""Add evaluation_configs + evaluation_config_results tables

Reusable, org-wide judge recipes for re-grading a frozen RAG eval run (an
``eval_results`` run) with a different judge model / custom rubric prompt /
metric set, plus the per-(config, source run) scored results. Purely additive
and independent of the existing single-run eval flow — ``eval_results`` is
untouched.

- ``evaluation_configs``: org-scoped, soft-deletable (``is_active`` /
  ``deleted_at``); name unique per org among live rows only.
- ``evaluation_config_results``: one row per re-graded question, all rows of a
  pass sharing ``config_run_id``; ``evaluation_config_id`` FK ON DELETE SET
  NULL (results survive a deleted config), ``eval_id`` FK ON DELETE CASCADE.

Revision ID: b2e8f4a1c9d5
Revises: a1c7e5b93d20
Create Date: 2026-09-09 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b2e8f4a1c9d5"
# Chained after dev's latest migration (merged from dev) so there is a single
# linear head — all are additive/independent, so order is irrelevant.
down_revision = "c2a9f1e7b4d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("judge_model", sa.String(length=120), nullable=False),
        sa.Column(
            "judge_engine",
            sa.String(length=32),
            nullable=False,
            server_default="deepeval",
        ),
        sa.Column("judge_prompt", sa.Text(), nullable=True),
        sa.Column(
            "metrics_enabled",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "metric_threshold",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.7"),
        ),
        sa.Column(
            "metric_thresholds",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.create_index(
        "ix_evaluation_configs_organization_id",
        "evaluation_configs",
        ["organization_id"],
    )
    # Name unique per org among live rows only — a soft-deleted name is reusable.
    op.create_index(
        "uq_evaluation_configs_org_name_active",
        "evaluation_configs",
        ["organization_id", "name"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "evaluation_config_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "evaluation_config_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("source_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("eval_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("config_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("config_run_number", sa.Integer(), nullable=False),
        sa.Column(
            "triggered_by",
            sa.String(length=32),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="completed",
        ),
        sa.Column("verdict", sa.String(length=16), nullable=True),
        sa.Column("judge_reasoning", sa.Text(), nullable=True),
        sa.Column(
            "metric_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            ["evaluation_config_id"],
            ["evaluation_configs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["eval_id"], ["evals.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_evaluation_config_results_organization_id",
        "evaluation_config_results",
        ["organization_id"],
    )
    op.create_index(
        "ix_evaluation_config_results_config_id",
        "evaluation_config_results",
        ["evaluation_config_id"],
    )
    op.create_index(
        "ix_evaluation_config_results_eval_id",
        "evaluation_config_results",
        ["eval_id"],
    )
    op.create_index(
        "ix_evaluation_config_results_config_run",
        "evaluation_config_results",
        ["config_run_id"],
    )
    op.create_index(
        "ix_evaluation_config_results_source_run",
        "evaluation_config_results",
        ["source_run_id"],
    )
    op.create_index(
        "ix_evaluation_config_results_config_run_number",
        "evaluation_config_results",
        ["evaluation_config_id", "config_run_number"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evaluation_config_results_config_run_number",
        table_name="evaluation_config_results",
    )
    op.drop_index(
        "ix_evaluation_config_results_source_run",
        table_name="evaluation_config_results",
    )
    op.drop_index(
        "ix_evaluation_config_results_config_run",
        table_name="evaluation_config_results",
    )
    op.drop_index(
        "ix_evaluation_config_results_eval_id",
        table_name="evaluation_config_results",
    )
    op.drop_index(
        "ix_evaluation_config_results_config_id",
        table_name="evaluation_config_results",
    )
    op.drop_index(
        "ix_evaluation_config_results_organization_id",
        table_name="evaluation_config_results",
    )
    op.drop_table("evaluation_config_results")

    op.drop_index(
        "uq_evaluation_configs_org_name_active",
        table_name="evaluation_configs",
    )
    op.drop_index(
        "ix_evaluation_configs_organization_id",
        table_name="evaluation_configs",
    )
    op.drop_table("evaluation_configs")
