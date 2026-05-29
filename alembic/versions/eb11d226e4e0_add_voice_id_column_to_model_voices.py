"""add voice_id column to model_voices

Revision ID: eb11d226e4e0
Revises: 426f072133d4
Create Date: 2026-05-28 17:05:27.743020

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'eb11d226e4e0'
down_revision = '426f072133d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('model_voices', sa.Column('voice_id', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('model_voices', 'voice_id')
