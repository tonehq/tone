"""merge tool and documents heads

Revision ID: 389d07c1be1d
Revises: b3c4d5e6f7a8, a1b2c3d4f5e6
Create Date: 2026-05-23 14:10:39.380318

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '389d07c1be1d'
down_revision = ('b3c4d5e6f7a8', 'a1b2c3d4f5e6')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
