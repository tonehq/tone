"""Add turn_metrics to call_metrics

Revision ID: a4e21c9b3d7f
Revises: 667f05ffd49b
Create Date: 2026-06-11 10:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'a4e21c9b3d7f'
down_revision = '667f05ffd49b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('call_metrics', sa.Column('turn_metrics', JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('call_metrics', 'turn_metrics')
