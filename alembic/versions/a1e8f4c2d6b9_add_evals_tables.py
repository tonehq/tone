"""add evals + eval_results tables

Moves RAG evaluation storage off the filesystem (``rag-testing/documents/<slug>/
questions.json`` and ``results/run-*.json``) into two org-scoped Postgres tables:

- ``evals`` — one row per KB upload: the LLM-generated Q&A dataset. ``UNIQUE
  (upload_id)`` so regeneration replaces the row in-place.
- ``eval_results`` — one row per run of an eval. FK'd to the specific
  ``ingestion_pipeline_runs`` row that was tested, so a regression can be
  attributed to a parser / tokeniser / embedder / vector-store recipe.
  ``UNIQUE (eval_id, run_number)`` enforces monotone run numbering per eval.

Revision ID: a1e8f4c2d6b9
Revises: b4a7f2c9e3d1
Create Date: 2026-07-24 15:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a1e8f4c2d6b9"
down_revision = "b4a7f2c9e3d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "knowledge_base_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "upload_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("uploads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("questions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("generated_by_model", sa.String(length=120), nullable=True),
        sa.Column("generation_prompt_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'ready'"),
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.UniqueConstraint("upload_id", name="uq_evals_upload_id"),
    )

    op.create_table(
        "eval_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "eval_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column(
            "ingestion_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingestion_pipeline_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("triggered_by", sa.String(length=32), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("answer_model", sa.String(length=120), nullable=True),
        sa.Column("judge_model", sa.String(length=120), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'running'"),
        ),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("per_question", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("eval_id", "run_number", name="uq_eval_results_eval_run"),
    )

    # Hot-path indices:
    # - "results for pipeline recipe X" — filter by ingestion_run_id, then status.
    op.create_index(
        "ix_eval_results_ingestion_run_status",
        "eval_results",
        ["ingestion_run_id", "status"],
    )
    # - "latest results for an eval" — eval_id + run_number DESC.
    op.create_index(
        "ix_eval_results_eval_run_desc",
        "eval_results",
        ["eval_id", sa.text("run_number DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_eval_results_eval_run_desc", table_name="eval_results")
    op.drop_index("ix_eval_results_ingestion_run_status", table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_table("evals")
