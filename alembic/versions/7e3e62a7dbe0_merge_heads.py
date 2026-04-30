"""merge heads

Revision ID: 7e3e62a7dbe0
Revises: af6013ae5648, c27f5a6dbd95
Create Date: 2026-04-30 15:54:19.638997

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7e3e62a7dbe0'
down_revision = ('af6013ae5648', 'c27f5a6dbd95')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
