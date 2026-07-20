"""merge contacts-directories + tool-executions heads

Revision ID: 0cf24b3d86dc
Revises: a4e9b1c7d3f5, 6ab783e9080f
Create Date: 2026-07-18 13:12:49.364456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0cf24b3d86dc'
down_revision = ('a4e9b1c7d3f5', '6ab783e9080f')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
