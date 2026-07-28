"""move procrastinate_job_id to ingestion_pipeline_runs; add active_ingestion_pipeline_run_id FK on knowledge_bases

procrastinate_job_id has been moved off knowledge_bases (where it was overwritten
on every reprocess/replace and lost history) onto ingestion_pipeline_runs — the
1:1 owner of each Procrastinate enqueue. knowledge_bases now carries a
denormalized FK, ``active_ingestion_pipeline_run_id``, so the current serving
run can be resolved with an O(1) lookup instead of iterating ``kb.runs`` in
Python.

No data backfill: the drop is unconditional (per product decision — historical
job ids on the KB row were low-value and callers only read the *current* one).

Revision ID: 7821c3c4d7b5
Revises: a1e8f4c2d6b9
Create Date: 2026-07-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "7821c3c4d7b5"
down_revision = "a1e8f4c2d6b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the misplaced column from knowledge_bases.
    op.drop_constraint(
        "fk_knowledge_bases_procrastinate_job_id",
        "knowledge_bases",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_knowledge_bases_procrastinate_job_id"),
        table_name="knowledge_bases",
    )
    op.drop_column("knowledge_bases", "procrastinate_job_id")

    # Move it to ingestion_pipeline_runs (one row per Procrastinate job).
    # ON DELETE SET NULL because procrastinate_jobs may prune completed jobs;
    # the run row must survive that pruning.
    op.add_column(
        "ingestion_pipeline_runs",
        sa.Column("procrastinate_job_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        op.f("ix_ingestion_pipeline_runs_procrastinate_job_id"),
        "ingestion_pipeline_runs",
        ["procrastinate_job_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_ingestion_pipeline_runs_procrastinate_job_id",
        "ingestion_pipeline_runs",
        "procrastinate_jobs",
        ["procrastinate_job_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Denormalized FK: KB → its currently active ingestion run. SET NULL on
    # run delete so a hard-deleted run doesn't leave a dangling KB pointer.
    op.add_column(
        "knowledge_bases",
        sa.Column(
            "active_ingestion_pipeline_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_knowledge_bases_active_ingestion_pipeline_run_id"),
        "knowledge_bases",
        ["active_ingestion_pipeline_run_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_knowledge_bases_active_ingestion_pipeline_run_id",
        "knowledge_bases",
        "ingestion_pipeline_runs",
        ["active_ingestion_pipeline_run_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_knowledge_bases_active_ingestion_pipeline_run_id",
        "knowledge_bases",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_knowledge_bases_active_ingestion_pipeline_run_id"),
        table_name="knowledge_bases",
    )
    op.drop_column("knowledge_bases", "active_ingestion_pipeline_run_id")

    op.drop_constraint(
        "fk_ingestion_pipeline_runs_procrastinate_job_id",
        "ingestion_pipeline_runs",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_ingestion_pipeline_runs_procrastinate_job_id"),
        table_name="ingestion_pipeline_runs",
    )
    op.drop_column("ingestion_pipeline_runs", "procrastinate_job_id")

    # Restore the old KB column exactly as 6bd88c8ee3dc created it.
    op.add_column(
        "knowledge_bases",
        sa.Column("procrastinate_job_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        op.f("ix_knowledge_bases_procrastinate_job_id"),
        "knowledge_bases",
        ["procrastinate_job_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_knowledge_bases_procrastinate_job_id",
        "knowledge_bases",
        "procrastinate_jobs",
        ["procrastinate_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
