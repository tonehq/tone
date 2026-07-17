"""add consolidated_transcript JSONB column to calls

Nullable JSONB column that holds the derived per-turn view produced by the
``consolidate_metrics`` post-call action (merges transcript + tool_executions
+ turn latency, grouped by pipecat turn number). Nullable because historical
calls have never been consolidated, and the column is populated
asynchronously by a background job — the row exists first, the column fills
in shortly after.

Revision ID: a9c1e5b3d7f2
Revises: a8a6d8cdfae3
Create Date: 2026-07-16 18:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'a9c1e5b3d7f2'
down_revision = 'a8a6d8cdfae3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'calls',
        sa.Column('consolidated_transcript', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('calls', 'consolidated_transcript')
