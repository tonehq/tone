"""drop legacy scalar metric columns from eval_results

The full DeepEval scorecard already lives in ``eval_results.metric_scores``
(JSONB), so the denormalized scalar columns ``correctness`` / ``groundedness`` /
``relevance`` were duplicates of three JSON entries. Metrics are now stored and
displayed from ``metric_scores`` alone — drop the scalars.

Contract step (destructive): ships together with the code that stops reading /
writing these columns. No backfill needed on downgrade — the columns are
re-created empty (the data of record is the JSON).

Revision ID: e7c2a9f4b1d6
Revises: d4a1f6c9b2e7
"""

from alembic import op
import sqlalchemy as sa


revision = "e7c2a9f4b1d6"
down_revision = "d4a1f6c9b2e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("eval_results", "correctness")
    op.drop_column("eval_results", "groundedness")
    op.drop_column("eval_results", "relevance")


def downgrade() -> None:
    # Re-add as nullable (no backfill — metric_scores JSONB remains the source).
    op.add_column("eval_results", sa.Column("correctness", sa.Float(), nullable=True))
    op.add_column("eval_results", sa.Column("groundedness", sa.Float(), nullable=True))
    op.add_column("eval_results", sa.Column("relevance", sa.Float(), nullable=True))
