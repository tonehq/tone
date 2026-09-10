"""Add human acceptance labels to eval_results

Human marks each scored answer Accept / Reject in the Eval-results tab. This is
config-independent ground truth stored on the frozen answer row, reused by every
judge to compute agreement %. Purely additive and nullable — the running release
ignores the columns and agreement stays "—" until someone labels a row, so this
is deploy-safe (no contract step).

Revision ID: d8a2f6c1e4b7
Revises: c7f1a3d9b6e2
Create Date: 2026-09-09 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "d8a2f6c1e4b7"
down_revision = "c7f1a3d9b6e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eval_results",
        sa.Column("human_verdict", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "eval_results",
        sa.Column("human_labeled_by", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "eval_results",
        sa.Column("human_labeled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("eval_results", "human_labeled_at")
    op.drop_column("eval_results", "human_labeled_by")
    op.drop_column("eval_results", "human_verdict")
