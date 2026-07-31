"""Restructure evals + eval_results as row-per-question / row-per-answer

Old shape: one ``evals`` row per upload with a ``questions`` JSONB holding the
whole set, one ``eval_results`` row per run with a ``per_question`` JSONB
holding every scored answer. That made individual questions / answers
unqueryable and forced the LLM loop to buffer everything in memory before a
single JSONB write.

New shape: one row per question in ``evals``, one row per scored answer in
``eval_results``. Doc-level bookkeeping (``name``, ``question_count``,
``status``, ``summary``) is dropped — derived on demand via COUNT / GROUP BY.
Run identity is the ``run_id`` UUID stamped identically on every row of a
run plus the per-``(upload_id, ingestion_run_id)`` ``run_number``.

Staging-only refactor. No backfill: existing rows are dropped and the next
auto-run / manual trigger regenerates.

Revision ID: e9b3a2f7c4d1
Revises: e5f8a3b2c9d1
Create Date: 2026-07-31 12:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e9b3a2f7c4d1"
down_revision = "e5f8a3b2c9d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the FK-holder first so the parent drop doesn't fail.
    op.drop_index("ix_eval_results_eval_run_desc", table_name="eval_results")
    op.drop_index("ix_eval_results_ingestion_run_status", table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_table("evals")

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
            index=True,
        ),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("question_ord", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=False),
        sa.Column("expected_source_snippet", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("generated_by_model", sa.String(length=120), nullable=True),
        sa.Column("generation_prompt_hash", sa.String(length=64), nullable=True),
        sa.Column("extras", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint("upload_id", "external_id", name="uq_evals_upload_external_id"),
    )
    op.create_index("ix_evals_upload_ord", "evals", ["upload_id", "question_ord"])

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
            index=True,
        ),
        sa.Column(
            "ingestion_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingestion_pipeline_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("triggered_by", sa.String(length=32), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("answer_model", sa.String(length=120), nullable=True),
        sa.Column("judge_model", sa.String(length=120), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'completed'"),
        ),
        sa.Column("actual_answer", sa.Text(), nullable=True),
        sa.Column(
            "retrieval_hit",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("retrieved_chunks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("verdict", sa.String(length=16), nullable=True),
        sa.Column("correctness", sa.Float(), nullable=True),
        sa.Column("groundedness", sa.Float(), nullable=True),
        sa.Column("relevance", sa.Float(), nullable=True),
        sa.Column("judge_reasoning", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("retrieval_error", sa.Text(), nullable=True),
        sa.Column("answer_error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("run_id", "eval_id", name="uq_eval_results_run_question"),
    )
    op.create_index("ix_eval_results_run_id", "eval_results", ["run_id"])
    op.create_index(
        "ix_eval_results_ingestion_run_number",
        "eval_results",
        ["ingestion_run_id", "run_number"],
    )
    op.create_index(
        "ix_eval_results_ingestion_run_verdict",
        "eval_results",
        ["ingestion_run_id", "verdict"],
    )
    op.create_index(
        "ix_eval_results_eval_run_desc",
        "eval_results",
        ["eval_id", sa.text("run_number DESC")],
    )


def downgrade() -> None:
    # Data loss is intentional per staging-only refactor decision. Restore the
    # old JSONB-shaped tables so an ``alembic downgrade`` round-trips
    # structurally.
    op.drop_index("ix_eval_results_eval_run_desc", table_name="eval_results")
    op.drop_index("ix_eval_results_ingestion_run_verdict", table_name="eval_results")
    op.drop_index("ix_eval_results_ingestion_run_number", table_name="eval_results")
    op.drop_index("ix_eval_results_run_id", table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_index("ix_evals_upload_ord", table_name="evals")
    op.drop_table("evals")

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
        sa.Column(
            "questions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
    op.create_index(
        "ix_eval_results_ingestion_run_status",
        "eval_results",
        ["ingestion_run_id", "status"],
    )
    op.create_index(
        "ix_eval_results_eval_run_desc",
        "eval_results",
        ["eval_id", sa.text("run_number DESC")],
    )
