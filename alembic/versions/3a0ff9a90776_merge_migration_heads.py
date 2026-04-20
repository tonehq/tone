"""merge migration heads

Revision ID: 3a0ff9a90776
Revises: 356e4af099b9, a1b2c3d4e5f6
Create Date: 2026-04-15 15:21:32.890129

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a0ff9a90776'
down_revision = ('356e4af099b9', 'a1b2c3d4e5f6')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
