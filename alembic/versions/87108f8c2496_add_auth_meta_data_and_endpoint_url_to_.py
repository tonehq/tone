"""add auth_meta_data and endpoint_url to models table

Revision ID: 87108f8c2496
Revises: 00950b136fcb
Create Date: 2026-04-10 13:26:38.427248

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '87108f8c2496'
down_revision = '00950b136fcb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('models', sa.Column('auth_meta_data', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('models', sa.Column('endpoint_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('models', 'endpoint_url')
    op.drop_column('models', 'auth_meta_data')
