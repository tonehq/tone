"""add is_template to tools

Revision ID: c1caad5095d0
Revises: 42c30a58e528
Create Date: 2026-05-08 07:18:39.146736

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1caad5095d0'
down_revision = '42c30a58e528'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tools', sa.Column('is_template', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('tools', 'is_template')
