"""add meta_data_schema to model_providers

Revision ID: 863e72f0e55a
Revises: eb11d226e4e0
Create Date: 2026-06-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '863e72f0e55a'
down_revision = 'eb11d226e4e0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('model_providers', sa.Column('meta_data_schema', JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('model_providers', 'meta_data_schema')
