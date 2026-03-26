"""add metrics column to call_logs

Revision ID: 19cebc5ddf80
Revises: 7a18e9b73090
Create Date: 2026-03-26 10:18:46.586467

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '19cebc5ddf80'
down_revision = '7a18e9b73090'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('call_logs', sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('call_logs', 'metrics')
