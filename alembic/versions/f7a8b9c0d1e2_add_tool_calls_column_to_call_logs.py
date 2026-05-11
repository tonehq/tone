"""add tool_calls column to call_logs

Revision ID: f7a8b9c0d1e2
Revises: e54cc342367e
Create Date: 2026-05-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f7a8b9c0d1e2'
down_revision = 'e54cc342367e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('call_logs', sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('call_logs', 'tool_calls')
