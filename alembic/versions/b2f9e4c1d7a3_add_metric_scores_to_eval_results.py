"""Add metric_scores JSONB column to eval_results

Stores the full per-metric scorecard produced by the DeepEval judge
(``{metric_name: {"score", "verdict", "reason"}}``). Legacy columns
(``correctness`` / ``groundedness`` / ``relevance`` / ``verdict`` /
``judge_reasoning``) keep flowing so every existing consumer works
unchanged; ``metric_scores`` is the superset.

Zero-downtime: nullable, no default, no backfill — old rows stay ``NULL``
and the service layer treats ``NULL`` as ``{}``.

Revision ID: b2f9e4c1d7a3
Revises: f8d1e5a7c2b4
Create Date: 2026-08-19 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b2f9e4c1d7a3"
down_revision = "f8d1e5a7c2b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eval_results",
        sa.Column(
            "metric_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("eval_results", "metric_scores")
