"""Add ingestion_stats JSONB to ingestion_pipeline_runs

Per-run parser/routing metrics (image / table / page counts, parse timings,
pipeline selected, etc.). Populated by ``IngestionRunService.complete_run``
from ``PdfRoutingService.build().metrics()``. NULL when the parser did not
produce metrics (e.g. non-docling parsers on non-PDF inputs).

Purely additive: nullable JSONB, no default, no backfill — historical runs
retain NULL, which matches the "no metrics captured" semantics.

Revision ID: e5f8a3b2c9d1
Revises: d4e7b2f9a1c8
Create Date: 2026-07-31 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e5f8a3b2c9d1"
down_revision = "d4e7b2f9a1c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingestion_pipeline_runs",
        sa.Column(
            "ingestion_stats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("ingestion_pipeline_runs", "ingestion_stats")
