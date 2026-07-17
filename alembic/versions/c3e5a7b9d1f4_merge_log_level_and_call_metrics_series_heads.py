"""merge log_level and call_metrics series-stats heads

Unifies the two heads created when origin/staging (call-metrics series-stats +
consolidated-transcript migrations) merged into the pipeline-logging branch:
  - e1f2a3b4c5d6 (add log_level to organizations and agents)
  - b7d1e4a8c2f9 (add series stats columns to call_metrics)
Both branch from a8a6d8cdfae3. No schema changes here.

Revision ID: c3e5a7b9d1f4
Revises: e1f2a3b4c5d6, b7d1e4a8c2f9
Create Date: 2026-07-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3e5a7b9d1f4'
down_revision = ('e1f2a3b4c5d6', 'b7d1e4a8c2f9')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
