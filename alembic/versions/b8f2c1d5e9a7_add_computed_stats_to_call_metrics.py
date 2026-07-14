"""Add computed_stats to call_metrics

Persists summary statistics (avg / p50 / p99 for TTFB and user-bot latency)
derived from the raw sample arrays. Populated at write time by
``CallMetricsService.upsert_for_call`` so read paths no longer recompute on
every request. Legacy rows without this column keep working — the response
formatter falls back to on-the-fly computation when the value is ``NULL``.

Revision ID: b8f2c1d5e9a7
Revises: e8a3c5d9f1b2
Create Date: 2026-07-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'b8f2c1d5e9a7'
down_revision = 'e8a3c5d9f1b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('call_metrics', sa.Column('computed_stats', JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('call_metrics', 'computed_stats')
