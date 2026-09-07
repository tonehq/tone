"""add eval versioning + approval

Expand step of an expand→migrate→contract change:
- create ``eval_versions``
- add nullable ``eval_version_id`` to ``evals`` + ``eval_results``
- add ``evals.approval_status`` (NOT NULL, server_default 'approved' so existing
  rows stay valid and old code that omits it keeps working)
- backfill: one v1 version per upload, point its evals at it, stamp results

Tightening (evals.eval_version_id NOT NULL, swap the unique constraint to
(eval_version_id, external_id)) is deferred to a follow-up migration once new
code is deployed everywhere.

Revision ID: d4a1f6c9b2e7
Revises: f2c7a9e14b6d
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "d4a1f6c9b2e7"
down_revision = "f2c7a9e14b6d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. eval_versions
    op.create_table(
        "eval_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "upload_id",
            UUID(as_uuid=True),
            sa.ForeignKey("uploads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "knowledge_base_id",
            UUID(as_uuid=True),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="generated"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("generation_instructions", sa.Text(), nullable=True),
        sa.Column("generated_by_model", sa.String(length=120), nullable=True),
        sa.Column("generation_prompt_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("upload_id", "version_number", name="uq_eval_versions_upload_number"),
    )
    op.create_index("ix_eval_versions_organization_id", "eval_versions", ["organization_id"])
    op.create_index("ix_eval_versions_upload", "eval_versions", ["upload_id"])
    op.create_index("ix_eval_versions_knowledge_base_id", "eval_versions", ["knowledge_base_id"])

    # 2. evals: new columns (nullable version id; approval defaults to approved)
    op.add_column("evals", sa.Column("eval_version_id", UUID(as_uuid=True), nullable=True))
    op.add_column(
        "evals",
        sa.Column("approval_status", sa.String(length=16), nullable=False, server_default="approved"),
    )
    op.create_foreign_key(
        "fk_evals_eval_version_id",
        "evals",
        "eval_versions",
        ["eval_version_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_evals_version_id", "evals", ["eval_version_id"])

    # 3. eval_results: version stamp (SET NULL so a result survives version delete)
    op.add_column("eval_results", sa.Column("eval_version_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_eval_results_eval_version_id",
        "eval_results",
        "eval_versions",
        ["eval_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_eval_results_version_id", "eval_results", ["eval_version_id"])

    # 4. Backfill — one v1 version per upload that already has evals.
    op.execute(
        """
        INSERT INTO eval_versions (
            id, organization_id, upload_id, knowledge_base_id, version_number,
            source, status, generated_by_model, generation_prompt_hash,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            agg.organization_id,
            agg.upload_id,
            agg.knowledge_base_id,
            1,
            CASE WHEN agg.all_manual THEN 'manual' ELSE 'generated' END,
            'finalized',
            agg.generated_by_model,
            agg.generation_prompt_hash,
            now(),
            now()
        FROM (
            SELECT
                upload_id,
                (array_agg(organization_id))[1] AS organization_id,
                (array_agg(knowledge_base_id))[1] AS knowledge_base_id,
                bool_and(coalesce(generated_by_model, '') = 'manual') AS all_manual,
                (array_agg(generated_by_model))[1] AS generated_by_model,
                (array_agg(generation_prompt_hash))[1] AS generation_prompt_hash
            FROM evals
            GROUP BY upload_id
        ) agg
        """
    )
    op.execute(
        """
        UPDATE evals e
        SET eval_version_id = v.id
        FROM eval_versions v
        WHERE v.upload_id = e.upload_id
          AND v.version_number = 1
          AND e.eval_version_id IS NULL
        """
    )
    # Existing rows are already 'approved' via the column server_default.
    op.execute(
        """
        UPDATE eval_results r
        SET eval_version_id = e.eval_version_id
        FROM evals e
        WHERE e.id = r.eval_id
          AND r.eval_version_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_eval_results_version_id", table_name="eval_results")
    op.drop_constraint("fk_eval_results_eval_version_id", "eval_results", type_="foreignkey")
    op.drop_column("eval_results", "eval_version_id")

    op.drop_index("ix_evals_version_id", table_name="evals")
    op.drop_constraint("fk_evals_eval_version_id", "evals", type_="foreignkey")
    op.drop_column("evals", "approval_status")
    op.drop_column("evals", "eval_version_id")

    op.drop_index("ix_eval_versions_knowledge_base_id", table_name="eval_versions")
    op.drop_index("ix_eval_versions_upload", table_name="eval_versions")
    op.drop_index("ix_eval_versions_organization_id", table_name="eval_versions")
    op.drop_table("eval_versions")
