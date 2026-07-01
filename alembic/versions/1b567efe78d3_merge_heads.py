"""merge heads

Revision ID: 1b567efe78d3
Revises: d5f2c8a91e73, b7c3f1a9d2e4
Create Date: 2026-07-01 16:02:51.206120

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1b567efe78d3'
down_revision = ('d5f2c8a91e73', 'b7c3f1a9d2e4')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
